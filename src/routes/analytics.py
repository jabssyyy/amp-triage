"""Phase 9 — Calibration and Trend Analytics.

Implements calibration curves, hit-rate progression per round, cumulative chemotype
diversity across rounds, and biophysical property distributions of hits vs misses.

Strict Honesty Rules:
1. Calibration buckets with n < 3 return observed_hit_rate = null (no rate from 2 points).
2. Seeded experiments (source='seeded_public') are labelled and distinct from real wet-lab results.
3. Empty states for unpopulated projects return clean nulls/empty lists without fake data.
4. Uses exact AgglomerativeClustering (cosine, average, 0.10 threshold) matching audit_validation.py.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, Query
from sklearn.cluster import AgglomerativeClustering
from sqlalchemy import select
from sqlalchemy.orm import Session

import config as C
from db import get_db
from models_db import Experiment, Project, Run, RunItem
from schemas import AnalyticsOut, CalibrationBucket, RoundStat
from scientist import compute_properties

router = APIRouter(prefix="/analytics", tags=["analytics"])

def _get_normalized_embedding(seq: str) -> np.ndarray | None:
    try:
        from score import _embedding_cache, _normalize, embed_on_the_fly

        seq_to_idx, _, normalized = _embedding_cache()
        if seq in seq_to_idx:
            return normalized[seq_to_idx[seq]]

        raw = embed_on_the_fly([seq])
        return _normalize(raw)[0]
    except Exception:
        return None


def _count_chemotypes(sequences: list[str], threshold: float = 0.10) -> int:
    """Computes distinct chemotype clusters using the standard cosine distance threshold."""
    if not sequences:
        return 0
    unique_seqs = list(dict.fromkeys(sequences))
    if len(unique_seqs) <= 1:
        return len(unique_seqs)

    embs = []
    for s in unique_seqs:
        e = _get_normalized_embedding(s)
        if e is not None:
            embs.append(e)

    if len(embs) < 2:
        return len(embs)

    arr = np.array(embs, dtype=np.float32)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=threshold,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(arr)
    return int(len(set(labels)))


@router.get("", response_model=AnalyticsOut)
def get_analytics(
    project_id: int | None = Query(default=None, description="Campaign project ID filter"),
    include_seeded: bool = Query(default=True, description="Include seeded DBAASP experiments"),
    db: Session = Depends(get_db),
):
    """Calculates model calibration, hit rate trends, and chemotype coverage across rounds."""
    # 1. Fetch runs
    run_stmt = select(Run).order_by(Run.created_at.asc())
    if project_id is not None:
        run_stmt = run_stmt.where(Run.project_id == project_id)
    runs = list(db.execute(run_stmt).scalars().all())

    # 2. Fetch experiments
    exp_stmt = select(Experiment).order_by(Experiment.tested_at.asc())
    if project_id is not None:
        exp_stmt = exp_stmt.where(Experiment.project_id == project_id)
    if not include_seeded:
        exp_stmt = exp_stmt.where(Experiment.source == "wet_lab")
    experiments = list(db.execute(exp_stmt).scalars().all())

    n_runs = len(runs)
    n_experiments = len(experiments)

    # 3. Overall hit rate
    hits_count = sum(1 for e in experiments if e.outcome == "hit")
    overall_hit_rate = round(hits_count / n_experiments, 4) if n_experiments > 0 else None

    # 4. Calibration: Bucket experiments by predicted p_active from RunItem
    # Define 5 standard buckets
    bucket_ranges = [
        (0.0, 0.2),
        (0.2, 0.4),
        (0.4, 0.6),
        (0.6, 0.8),
        (0.8, 1.0),
    ]
    bucket_data = {br: {"n": 0, "hits": 0} for br in bucket_ranges}

    # Map run items for fast lookup
    item_map: dict[int, RunItem] = {}
    seq_p_active_map: dict[str, float] = {}
    for r in runs:
        for it in r.items:
            item_map[it.id] = it
            seq_p_active_map[it.sequence] = it.p_active

    for exp in experiments:
        p_act: float | None = None
        if exp.run_item_id and exp.run_item_id in item_map:
            p_act = item_map[exp.run_item_id].p_active
        elif exp.sequence in seq_p_active_map:
            p_act = seq_p_active_map[exp.sequence]

        if p_act is not None:
            # Place in appropriate bucket
            for lower, upper in bucket_ranges:
                if (lower <= p_act < upper) or (upper == 1.0 and lower <= p_act <= 1.0):
                    bucket_data[(lower, upper)]["n"] += 1
                    if exp.outcome == "hit":
                        bucket_data[(lower, upper)]["hits"] += 1
                    break

    calibration_buckets: list[CalibrationBucket] = []
    for (lower, upper), stats in bucket_data.items():
        n = stats["n"]
        # HONESTY RULE: A bucket with n < 3 must return observed_hit_rate=null
        if n >= 3:
            obs_rate = round(stats["hits"] / n, 4)
        else:
            obs_rate = None

        calibration_buckets.append(
            CalibrationBucket(
                predicted_lower=lower,
                predicted_upper=upper,
                n=n,
                observed_hit_rate=obs_rate,
            )
        )

    # 5. Round Stats (Hit rate progression)
    rounds: list[RoundStat] = []
    accumulated_sequences: list[str] = []
    cumulative_chemotypes: list[int] = []

    for run in runs:
        run_item_ids = {it.id for it in run.items}
        run_seqs = {it.sequence for it in run.items}

        # Experiments matching this run
        run_exps = [
            e for e in experiments
            if (e.run_item_id and e.run_item_id in run_item_ids) or (e.sequence in run_seqs)
        ]

        n_tested = len(run_exps)
        n_hits = sum(1 for e in run_exps if e.outcome == "hit")
        round_hit_rate = round(n_hits / n_tested, 4) if n_tested > 0 else None

        rounds.append(
            RoundStat(
                run_id=run.id,
                created_at=run.created_at,
                n_tested=n_tested,
                n_hits=n_hits,
                hit_rate=round_hit_rate,
            )
        )

        # Accumulate selected sequences to evaluate cumulative scaffold expansion
        accumulated_sequences.extend(list(run_seqs))
        cumulative_chemotypes.append(_count_chemotypes(accumulated_sequences))

    return AnalyticsOut(
        project_id=project_id,
        n_runs=n_runs,
        n_experiments=n_experiments,
        overall_hit_rate=overall_hit_rate,
        calibration=calibration_buckets,
        rounds=rounds,
        cumulative_chemotypes=cumulative_chemotypes,
    )


@router.get("/properties-breakdown")
def get_properties_breakdown(
    project_id: int | None = Query(default=None),
    include_seeded: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """Computes mean charge, hydrophobic moment, and length for observed hits vs misses."""
    exp_stmt = select(Experiment)
    if project_id is not None:
        exp_stmt = exp_stmt.where(Experiment.project_id == project_id)
    if not include_seeded:
        exp_stmt = exp_stmt.where(Experiment.source == "wet_lab")
    experiments = list(db.execute(exp_stmt).scalars().all())

    hits_seqs = [e.sequence for e in experiments if e.outcome == "hit"]
    miss_seqs = [e.sequence for e in experiments if e.outcome in ("miss", "toxic")]

    def _calc_stats(seqs: list[str]) -> dict[str, Any]:
        if not seqs:
            return {"n": 0, "mean_charge": None, "mean_uH": None, "mean_length": None}
        charges = []
        uHs = []
        lengths = []
        for s in seqs:
            try:
                p = compute_properties(s)
                charges.append(p["net_charge_pH7"])
                uHs.append(p["hydrophobic_moment_uH"])
                lengths.append(p["length"])
            except Exception:
                continue

        if not charges:
            return {"n": 0, "mean_charge": None, "mean_uH": None, "mean_length": None}

        return {
            "n": len(charges),
            "mean_charge": round(float(np.mean(charges)), 2),
            "mean_uH": round(float(np.mean(uHs)), 3),
            "mean_length": round(float(np.mean(lengths)), 1),
        }

    return {
        "hits": _calc_stats(hits_seqs),
        "misses": _calc_stats(miss_seqs),
    }
