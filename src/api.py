"""FastAPI Backend for AMP Triage (PharmaMind).

Wraps the core Python scoring, selection, validation, and scientist-assistant
engines without reimplementing any scientific math in TypeScript/JavaScript.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import config as C
from peptides import is_standard_peptide
from scientist import (
    compare_structures,
    compute_properties,
    fetch_pubmed_evidence,
    fetch_structure,
    generate_helical_wheel_svg,
    generate_relationship_graph,
)
from score import embed_on_the_fly, score_frame, score_one
from validate import run_validation

# --- persistence (phase 6) ------------------------------------------------
# api.py is a thin composition root: it imports routers and includes them.
# New endpoints belong in their own module under routes/, one per parallel
# track, so two people never edit this file at the same time.
import crud
from auth import get_current_user_optional
from db import SessionLocal, init_db
from routes import experiments as experiments_routes
from routes import runs as runs_routes

# Safely load local select.py to prevent collision with Python's built-in select module
_sel_spec = importlib.util.spec_from_file_location("amp_select", SRC_DIR / "select.py")
_sel_mod = importlib.util.module_from_spec(_sel_spec)
_sel_spec.loader.exec_module(_sel_mod)
select_engine = _sel_mod.select

# In-memory validation cache so /validate responds instantly (<2ms) during demos
_VALIDATION_CACHE: dict[str, dict[str, Any]] = {}


# --- Lifespan: warm ESM2 and precompute validation cache at startup ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Warm ESM2 with a dummy sequence so uncached what-if scoring is fast
    try:
        embed_on_the_fly(["KWKLFKKIGAVLKVL"])
    except Exception as e:
        print(f"Warning: ESM2 warming encountered error: {e}")

    # 2. Precompute validation cache for all priority species
    for sp in C.PRIORITY_SPECIES:
        try:
            _VALIDATION_CACHE[sp] = run_validation(species=sp, k=C.DEFAULT_K)
        except Exception as e:
            print(f"Warning: Failed to precompute validation for {sp}: {e}")

    # phase 6: make sure the database exists before serving
    try:
        init_db()
    except Exception as e:
        print(f"Warning: database init failed, persistence disabled: {e}")

    yield


app = FastAPI(
    title="AMP Triage API",
    description="Intelligent Drug Discovery Assistant for Antimicrobial Peptides",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request & Response Models -----------------------------------------------

class ScoreRequest(BaseModel):
    sequence: str = Field(..., description="Amino acid sequence (standard residues, len >= 5)")
    species: str = Field(..., description="Target WHO priority pathogen")


class ScoreResponse(BaseModel):
    sequence: str
    species: str
    p_active: float
    p_toxic: float
    q: float
    cached: bool


class ShortlistRequest(BaseModel):
    sequences: list[str] = Field(..., description="List of peptide sequences in candidate pool")
    species: str = Field(..., description="Target WHO priority pathogen")
    project_id: int | None = Field(default=None, description="Campaign this run belongs to")
    exclude_tested: bool = Field(default=False, description="Skip peptides this lab already tested")
    penalise_tested: bool = Field(default=False, description="Down-weight rather than drop them")
    k: int = Field(default=C.DEFAULT_K, description="Testing budget (number of picks)")
    theta: float = Field(default=C.DEFAULT_THETA, description="Quality vs diversity tuning parameter")


class ShortlistItem(BaseModel):
    rank: int
    sequence: str
    q_i: float
    q_i_scaled: float
    p_active: float
    p_toxic: float
    marginal_log_gain: float
    similarity_to_nearest_selected: float


class ShortlistResponse(BaseModel):
    run_id: int | None = None
    n_excluded: int = 0
    excluded_sequences: list[str] = Field(default_factory=list)
    logdet: float
    theta: float
    items: list[ShortlistItem]
    baseline_top_n: list[str]


class ValidateRequest(BaseModel):
    species: str = Field(default="Escherichia coli", description="Target WHO priority pathogen")
    k: int = Field(default=C.DEFAULT_K, description="Testing budget")


class ValidateResponse(BaseModel):
    greedy_recovered: int
    topn_recovered: int
    n_hidden: int
    k: int
    greedy_chemotypes: float | None = None
    topn_chemotypes: float | None = None
    total_clusters: int | None = None


class SpeciesMetric(BaseModel):
    name: str
    n_train: int
    cv_roc_auc: float
    cv_roc_auc_std: float
    confidence: str


class CompareRequest(BaseModel):
    sequences: list[str] = Field(..., description="Two peptide sequences to compare")
    species: str = Field(default="Escherichia coli", description="Pathogen context for scoring")


class CompareResponse(BaseModel):
    sequences: list[str]
    species: str
    properties: list[dict[str, Any]]
    wheel_svgs: list[str]
    cosine_similarity: float
    embedding_distance: float
    scores: list[dict[str, Any]]


# --- Core Phase 2-4 Endpoints ------------------------------------------------

@app.post("/score", response_model=ScoreResponse)
def score_peptide(req: ScoreRequest):
    """Scores a single candidate sequence against a pathogen and human RBC toxicity."""
    clean_seq = req.sequence.strip().upper()
    if len(clean_seq) < C.MIN_PEPTIDE_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Sequence length must be at least {C.MIN_PEPTIDE_LEN} residues (got {len(clean_seq)})",
        )
    if not is_standard_peptide(clean_seq):
        raise HTTPException(
            status_code=400,
            detail=f"Sequence contains invalid or non-standard amino acid characters: {req.sequence}",
        )
    if req.species not in C.PRIORITY_SPECIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid species {req.species!r}. Must be one of {list(C.PRIORITY_SPECIES)}",
        )

    res = score_one(clean_seq, req.species)
    return ScoreResponse(
        sequence=res["sequence"],
        species=res["species"],
        p_active=round(res["p_active"], 4),
        p_toxic=round(res["p_toxic"], 4),
        q=round(res["q"], 4),
        cached=res["cached"],
    )


@app.post("/shortlist", response_model=ShortlistResponse)
def generate_shortlist(
    req: ShortlistRequest,
    current_user=Depends(get_current_user_optional),
):
    """Generates a diversity-aware, budget-constrained shortlist using log-det greedy selection."""
    if req.species not in C.PRIORITY_SPECIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid species {req.species!r}. Must be one of {list(C.PRIORITY_SPECIES)}",
        )
    if not req.sequences:
        raise HTTPException(status_code=400, detail="Candidate sequences pool cannot be empty")

    clean_seqs = [s.strip().upper() for s in req.sequences]
    bad = [s for s in clean_seqs if not is_standard_peptide(s)]
    if bad:
        raise HTTPException(
            status_code=400,
            detail=f"{len(bad)} sequence(s) have non-standard residues or are shorter than {C.MIN_PEPTIDE_LEN} (e.g. {bad[0]!r})",
        )

    # Institutional memory (phase 8). The lab's history is applied to the POOL, before
    # the selection engine runs. select.py stays untouched and its 24 checks stay valid.
    excluded_seqs: list[str] = []
    already_tested: dict = {}
    if req.exclude_tested or req.penalise_tested:
        try:
            with SessionLocal() as db:
                already_tested = crud.tested_sequences(
                    db, lab_id=getattr(current_user, "lab_id", None)
                )
        except Exception as e:
            print(f"Warning: lab memory unavailable, proceeding without it: {e}")

    if req.exclude_tested and already_tested:
        kept = [s for s in clean_seqs if s not in already_tested]
        excluded_seqs = [s for s in clean_seqs if s in already_tested]
        # Never empty the pool: if the lab has tested everything, fall back to scoring
        # the full pool rather than returning nothing.
        if kept:
            clean_seqs = kept
        else:
            excluded_seqs = []

    try:
        scored = score_frame(clean_seqs, req.species)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring error: {e}")

    emb = scored["embeddings_normalized"]
    p_act = scored["p_active"]
    p_tox = scored["p_toxic"]
    seqs = scored["sequences"]

    if req.penalise_tested and already_tested:
        # Soft version of exclusion: a peptide already tested can still be picked, but
        # has to be clearly better to earn the slot. A confirmed miss is discounted
        # harder than an untested one, a confirmed hit barely at all.
        decay = {"hit": 0.95, "inconclusive": 0.5, "miss": 0.2, "toxic": 0.1}
        p_act = p_act.copy()
        for i, sq in enumerate(seqs):
            rec = already_tested.get(sq)
            if rec is not None:
                p_act[i] *= decay.get(rec.best_outcome or "miss", 0.3)

    res = select_engine(emb, p_act, p_tox, k=req.k, theta=req.theta)
    picks = res["selected"]

    items = []
    for rank, idx in enumerate(picks, start=1):
        items.append(
            ShortlistItem(
                rank=rank,
                sequence=seqs[idx],
                q_i=round(float(res["q"][idx]), 4),
                q_i_scaled=round(float(res["q_scaled"][idx]), 6),
                p_active=round(float(p_act[idx]), 4),
                p_toxic=round(float(p_tox[idx]), 4),
                marginal_log_gain=round(float(res["marginal_gains"][rank - 1]), 4),
                similarity_to_nearest_selected=round(float(res["nearest_selected_similarity"][rank - 1]), 4),
            )
        )

    baseline_top_n_seqs = [seqs[i] for i in res["baseline_top_n"]]

    # Persist the run. Wrapped defensively on purpose: a database failure must never
    # take down the shortlist endpoint, which is the core demo path.
    run_id = None
    try:
        with SessionLocal() as db:
            saved = crud.save_run(
                db,
                species=req.species,
                k=int(req.k),
                theta=float(req.theta),
                logdet=float(res["logdet"]),
                pool_size=len(clean_seqs),
                items=[i.model_dump() for i in items],
                baseline_top_n=baseline_top_n_seqs,
                # attribution when signed in; anonymous runs stay supported
                scientist_id=getattr(current_user, "id", None),
                project_id=req.project_id,
                excluded_tested=bool(req.exclude_tested),
                n_excluded=len(excluded_seqs),
            )
            run_id = saved.id
    except Exception as e:
        print(f"Warning: could not persist run: {e}")

    return ShortlistResponse(
        run_id=run_id,
        n_excluded=len(excluded_seqs),
        excluded_sequences=excluded_seqs[:50],
        logdet=round(res["logdet"], 4),
        theta=float(req.theta),
        items=items,
        baseline_top_n=baseline_top_n_seqs,
    )


@app.post("/validate", response_model=ValidateResponse)
def validate_held_out(req: ValidateRequest, refresh: bool = Query(default=False)):
    """Runs recovery and chemotype benchmark on held-out test split (served from cache unless refresh=true)."""
    if req.species not in C.PRIORITY_SPECIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid species {req.species!r}. Must be one of {list(C.PRIORITY_SPECIES)}",
        )

    if not refresh and req.species in _VALIDATION_CACHE and req.k == C.DEFAULT_K:
        val_res = _VALIDATION_CACHE[req.species]
    else:
        val_res = run_validation(species=req.species, k=req.k)
        if req.k == C.DEFAULT_K:
            _VALIDATION_CACHE[req.species] = val_res

    return ValidateResponse(
        greedy_recovered=val_res["greedy_recovered"],
        topn_recovered=val_res["topn_recovered"],
        n_hidden=val_res["n_actives"],
        k=val_res["k"],
        greedy_chemotypes=val_res["greedy_chemotypes_mean"],
        topn_chemotypes=val_res["topn_chemotypes_mean"],
        total_clusters=val_res["total_clusters"],
    )


@app.get("/species", response_model=list[SpeciesMetric])
def get_species_metrics():
    """Returns trained species with model metrics and evidence-based confidence levels."""
    metrics_file = C.REPORTS / "activity_metrics.json"
    if not metrics_file.exists():
        raise HTTPException(status_code=500, detail="Activity metrics file not found")

    with open(metrics_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for sp in C.PRIORITY_SPECIES:
        sp_data = data.get(sp, {})
        n_train = sp_data.get("n_train", 0)
        cv = sp_data.get("cv", {})
        roc_auc = cv.get("roc_auc", 0.0)
        roc_auc_std = cv.get("roc_auc_std", 0.0)

        # Assign confidence based strictly on metrics in activity_metrics.json
        if roc_auc >= 0.73 and n_train >= 500:
            confidence = "high"
        elif roc_auc >= 0.70 and n_train >= 100:
            confidence = "moderate"
        else:
            confidence = "low"

        results.append(
            SpeciesMetric(
                name=sp,
                n_train=n_train,
                cv_roc_auc=round(roc_auc, 3),
                cv_roc_auc_std=round(roc_auc_std, 3),
                confidence=confidence,
            )
        )

    return results


# --- Phase 5 Scientist-Assistant Endpoints -----------------------------------

@app.get("/properties")
def get_properties(sequence: str = Query(..., description="Peptide amino acid sequence")):
    """Returns biochemical properties, net charge at pH 7, and Eisenberg hydrophobic moment."""
    clean_seq = sequence.strip().upper()
    if not is_standard_peptide(clean_seq):
        raise HTTPException(status_code=400, detail="Invalid sequence containing non-standard amino acids")
    return compute_properties(clean_seq)


@app.get("/wheel")
def get_helical_wheel(sequence: str = Query(..., description="Peptide amino acid sequence")):
    """Returns a standalone, deterministic SVG helical wheel diagram with hydrophobic moment vector."""
    clean_seq = sequence.strip().upper()
    if not is_standard_peptide(clean_seq):
        raise HTTPException(status_code=400, detail="Invalid sequence containing non-standard amino acids")
    svg_content = generate_helical_wheel_svg(clean_seq)
    return Response(content=svg_content, media_type="image/svg+xml")


@app.post("/compare", response_model=CompareResponse)
def compare_peptides(req: CompareRequest):
    """Compares two candidate sequences side-by-side: properties, wheels, and exact embedding distance."""
    if len(req.sequences) != 2:
        raise HTTPException(status_code=400, detail="Compare endpoint requires exactly two sequences in 'sequences'")

    clean_seqs = [s.strip().upper() for s in req.sequences]
    for s in clean_seqs:
        if not is_standard_peptide(s):
            raise HTTPException(status_code=400, detail=f"Invalid sequence: {s}")

    props = [compute_properties(s) for s in clean_seqs]
    wheels = [generate_helical_wheel_svg(s) for s in clean_seqs]

    scored = score_frame(clean_seqs, req.species)
    emb = scored["embeddings_normalized"]
    cos_sim = float(np.dot(emb[0], emb[1]))
    cos_dist = float(1.0 - cos_sim)

    scores = [
        {
            "sequence": clean_seqs[i],
            "p_active": round(float(scored["p_active"][i]), 4),
            "p_toxic": round(float(scored["p_toxic"][i]), 4),
            "q": round(float(scored["p_active"][i] * (1.0 - scored["p_toxic"][i])), 4),
        }
        for i in range(2)
    ]

    return CompareResponse(
        sequences=clean_seqs,
        species=req.species,
        properties=props,
        wheel_svgs=wheels,
        cosine_similarity=round(cos_sim, 4),
        embedding_distance=round(cos_dist, 4),
        scores=scores,
    )


@app.get("/evidence")
def get_evidence(
    sequence: str = Query(..., description="Peptide sequence"),
    species: str = Query(default="Escherichia coli", description="Target pathogen"),
):
    """Retrieves real PubMed abstracts and antimicrobial grounding via NCBI E-utilities."""
    clean_seq = sequence.strip().upper()
    return fetch_pubmed_evidence(clean_seq, species)


@app.get("/graph")
def get_knowledge_graph(
    sequence: str = Query(..., description="Peptide sequence"),
    species: str = Query(default="Escherichia coli", description="Target pathogen"),
):
    """Generates node/edge relationship graph data for Compound - Pathogen - Resistance - Papers."""
    clean_seq = sequence.strip().upper()
    return generate_relationship_graph(clean_seq, species)


@app.get("/structure")
def get_structure(sequence: str = Query(..., description="Peptide sequence")):
    """Multi-tier 3D structure resolution: Tier 1 Experimental (RCSB PDB), Tier 2 Predicted (ESMFold), Tier 3 Unavailable."""
    clean_seq = sequence.strip().upper()
    if not is_standard_peptide(clean_seq):
        raise HTTPException(status_code=400, detail="Invalid sequence containing non-standard amino acids")
    return fetch_structure(clean_seq)


@app.get("/structure/compare")
def compare_3d_structures(
    seq1: str = Query(None, description="First sequence"),
    seq2: str = Query(None, description="Second sequence"),
    sequences: str = Query(None, description="Comma-separated sequences A,B"),
):
    """Calculates RMSD only if BOTH structures are experimentally determined."""
    if sequences:
        parts = [p.strip().upper() for p in sequences.split(",")]
        if len(parts) == 2:
            seq1, seq2 = parts[0], parts[1]
    if not seq1 or not seq2:
        raise HTTPException(status_code=400, detail="Please provide two sequences via seq1 & seq2 or sequences=A,B")

    return compare_structures(seq1.strip().upper(), seq2.strip().upper())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)


# --- routers ---------------------------------------------------------------
# Additive only. Every original science endpoint above stays exactly as it was.
from routes import auth as auth_routes
from routes import projects as projects_routes
from routes import analytics as analytics_routes

app.include_router(runs_routes.router)
app.include_router(auth_routes.router)
app.include_router(projects_routes.router)
app.include_router(experiments_routes.router)
app.include_router(analytics_routes.router)

