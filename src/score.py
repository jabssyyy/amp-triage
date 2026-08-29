"""Phase 2 - score a peptide: P(active) against a species, P(toxic), and q_i.

Contract (locked -- phase 4+ builds against this, do not change signatures silently):

    score_one(sequence, species)  -> {"p_active", "p_toxic", "q", "cached"}
    score_frame(sequences, species) -> {"sequences", "p_active", "p_toxic",
                                        "embeddings_normalized", "cached"}

Sequences already in the embedding cache are looked up. Anything else -- a peptide
the researcher typed or edited in the what-if tab -- is embedded on the fly with the
same ESM2 model, so hypothetical sequences score identically to known ones.

Run: python src/score.py --sequence KWKLFKKIGAVLKVL --species "Escherichia coli"
"""
from __future__ import annotations

import argparse
import time
from functools import lru_cache

import numpy as np

import config as C
from peptides import is_standard_peptide

_ESM_CACHE: dict = {}


def species_slug(species: str) -> str:
    return species.lower().replace(" ", "_").replace(".", "")


@lru_cache(maxsize=1)
def _embedding_cache() -> tuple[dict[str, int], np.ndarray, np.ndarray]:
    cache = np.load(C.EMBEDDING_CACHE, allow_pickle=True)
    seqs = [str(s) for s in cache["sequences"]]
    return {s: i for i, s in enumerate(seqs)}, cache["raw"], cache["normalized"]


@lru_cache(maxsize=8)
def _model(name: str):
    from train_common import load_model
    return load_model(name)


def _load_esm():
    """Lazily load ESM2 only when an uncached sequence actually needs embedding."""
    if "model" not in _ESM_CACHE:
        import esm
        import torch
        model, alphabet = getattr(esm.pretrained, C.ESM_MODEL)()
        model.eval()
        _ESM_CACHE.update(
            model=model, converter=alphabet.get_batch_converter(),
            layer=model.num_layers, torch=torch,
        )
    return _ESM_CACHE


def embed_on_the_fly(sequences: list[str]) -> np.ndarray:
    """Mean-pooled ESM2 embeddings for sequences not in the cache."""
    ctx = _load_esm()
    data = [("s%d" % i, s) for i, s in enumerate(sequences)]
    _, _, tokens = ctx["converter"](data)
    with ctx["torch"].no_grad():
        reps = ctx["model"](tokens, repr_layers=[ctx["layer"]])["representations"][ctx["layer"]]
    out = np.zeros((len(sequences), reps.shape[-1]), dtype=np.float32)
    for i, s in enumerate(sequences):
        out[i] = reps[i, 1:len(s) + 1].mean(0).numpy()
    return out


def _normalize(matrix: np.ndarray) -> np.ndarray:
    relu = np.maximum(matrix, 0.0)
    norms = np.linalg.norm(relu, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (relu / norms).astype(np.float32)


def score_frame(sequences: list[str], species: str) -> dict:
    """Score many sequences at once. Returns arrays aligned to `sequences`."""
    if species not in C.PRIORITY_SPECIES:
        raise ValueError("no model for %r; trained species are %s"
                         % (species, list(C.PRIORITY_SPECIES)))
    clean = [str(s).strip().upper() for s in sequences]
    bad = [s for s in clean if not is_standard_peptide(s)]
    if bad:
        raise ValueError(
            "%d sequence(s) are not embeddable (non-standard residues or shorter than %d), "
            "e.g. %r" % (len(bad), C.MIN_PEPTIDE_LEN, bad[0])
        )

    index, raw_all, norm_all = _embedding_cache()
    raw = np.zeros((len(clean), raw_all.shape[1]), dtype=np.float32)
    cached = np.zeros(len(clean), dtype=bool)
    missing = []
    for i, s in enumerate(clean):
        if s in index:
            raw[i] = raw_all[index[s]]
            cached[i] = True
        else:
            missing.append(i)
    if missing:
        fresh = embed_on_the_fly([clean[i] for i in missing])
        for row, i in enumerate(missing):
            raw[i] = fresh[row]

    activity = _model("activity_%s" % species_slug(species))
    toxicity = _model("toxicity_human_rbc")
    p_active = activity.predict_proba(raw)[:, 1]
    p_toxic = toxicity.predict_proba(raw)[:, 1]

    return {
        "sequences": clean,
        "p_active": p_active,
        "p_toxic": p_toxic,
        "embeddings_raw": raw,
        "embeddings_normalized": _normalize(raw),
        "cached": cached,
    }


def score_one(sequence: str, species: str) -> dict:
    out = score_frame([sequence], species)
    p_a, p_t = float(out["p_active"][0]), float(out["p_toxic"][0])
    return {
        "sequence": out["sequences"][0],
        "species": species,
        "p_active": p_a,
        "p_toxic": p_t,
        "q": p_a * (1.0 - p_t),
        "cached": bool(out["cached"][0]),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Score one peptide")
    ap.add_argument("--sequence", required=True)
    ap.add_argument("--species", required=True, choices=list(C.PRIORITY_SPECIES))
    args = ap.parse_args()

    start = time.time()
    result = score_one(args.sequence, args.species)
    elapsed = time.time() - start

    print("sequence   %s" % result["sequence"])
    print("species    %s" % result["species"])
    print("P(active)  %.4f" % result["p_active"])
    print("P(toxic)   %.4f" % result["p_toxic"])
    print("q_i        %.4f" % result["q"])
    print("(%s, %.3fs)" % ("cached embedding" if result["cached"] else "embedded live", elapsed))


if __name__ == "__main__":
    main()
