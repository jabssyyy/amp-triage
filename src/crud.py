"""Database operations shared across routers.

Kept separate from the routers so phase 8 can reuse the registry helpers without
importing phase 6b's HTTP layer.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select as sa_select
from sqlalchemy.orm import Session

from models_db import OUTCOME_RANK, PeptideRegistry, Run, RunItem, Scientist


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- runs ---------------------------------------------------------------------

def save_run(
    db: Session,
    *,
    species: str,
    k: int,
    theta: float,
    logdet: float,
    pool_size: int,
    items: list[dict],
    baseline_top_n: list[str] | None = None,
    project_id: int | None = None,
    pool_id: int | None = None,
    scientist_id: int | None = None,
    excluded_tested: bool = False,
    n_excluded: int = 0,
    label: str | None = None,
) -> Run:
    """Persist a selection and its shortlist.

    `items` are the dicts the /shortlist endpoint already returns, so the caller does
    not have to reshape anything. Scores are copied verbatim and frozen here — a
    shortlist is a record of a decision and must not drift when models are retrained.
    """
    # The shortlist screen re-runs on every slider move, so an unguarded save floods
    # history with near-identical rows and makes it useless during a demo. If the most
    # recent run had the same parameters, replace it rather than stacking another.
    latest = db.execute(
        sa_select(Run).order_by(Run.created_at.desc(), Run.id.desc()).limit(1)
    ).scalar_one_or_none()
    if (
        latest is not None
        and latest.label is None                 # never clobber a run someone named
        and latest.species == species
        and latest.k == k
        and abs(latest.theta - theta) < 1e-9
        and latest.pool_size == pool_size
        and latest.project_id == project_id
        and latest.scientist_id == scientist_id
    ):
        db.delete(latest)
        db.flush()

    top_set = set(baseline_top_n or [])
    run = Run(
        project_id=project_id,
        pool_id=pool_id,
        scientist_id=scientist_id,
        species=species,
        k=k,
        theta=theta,
        logdet=logdet,
        pool_size=pool_size,
        excluded_tested=excluded_tested,
        n_excluded=n_excluded,
        label=label,
    )
    db.add(run)
    db.flush()  # assign run.id without committing yet

    for it in items:
        db.add(RunItem(
            run_id=run.id,
            rank=int(it["rank"]),
            sequence=str(it["sequence"]),
            q_i=float(it["q_i"]),
            p_active=float(it["p_active"]),
            p_toxic=float(it["p_toxic"]),
            similarity_to_nearest=float(it.get("similarity_to_nearest_selected", 0.0)),
            marginal_log_gain=float(it.get("marginal_log_gain", 0.0)),
            is_diversity_pick=bool(top_set) and str(it["sequence"]) not in top_set,
        ))

    lab_id = _lab_of(db, scientist_id)
    for it in items:
        touch_selected(db, str(it["sequence"]), lab_id=lab_id)

    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, *, limit: int = 50, project_id: int | None = None,
              scientist_id: int | None = None) -> list[dict]:
    """History list. Returns plain dicts so the router stays thin."""
    counts = (
        sa_select(RunItem.run_id, func.count(RunItem.id).label("n"))
        .group_by(RunItem.run_id).subquery()
    )
    stmt = (
        sa_select(Run, counts.c.n, Scientist.full_name)
        .outerjoin(counts, counts.c.run_id == Run.id)
        .outerjoin(Scientist, Scientist.id == Run.scientist_id)
        .order_by(Run.created_at.desc())
        .limit(limit)
    )
    if project_id is not None:
        stmt = stmt.where(Run.project_id == project_id)
    if scientist_id is not None:
        stmt = stmt.where(Run.scientist_id == scientist_id)

    out = []
    for run, n_items, sci_name in db.execute(stmt).all():
        out.append({
            "id": run.id, "species": run.species, "k": run.k, "theta": run.theta,
            "logdet": run.logdet, "pool_size": run.pool_size,
            "n_items": int(n_items or 0), "n_excluded": run.n_excluded,
            "label": run.label, "project_id": run.project_id,
            "scientist_id": run.scientist_id, "scientist_name": sci_name,
            "created_at": run.created_at,
        })
    return out


def get_run(db: Session, run_id: int) -> Run | None:
    return db.get(Run, run_id)


def delete_run(db: Session, run_id: int) -> bool:
    run = db.get(Run, run_id)
    if run is None:
        return False
    db.delete(run)          # run_item rows cascade
    db.commit()
    return True


# --- peptide registry (lab memory; phase 8 builds on this) -----------------------

def _lab_of(db: Session, scientist_id: int | None) -> int | None:
    if scientist_id is None:
        return None
    sci = db.get(Scientist, scientist_id)
    return sci.lab_id if sci else None


def _registry_row(db: Session, sequence: str, lab_id: int | None) -> PeptideRegistry:
    stmt = sa_select(PeptideRegistry).where(
        PeptideRegistry.sequence == sequence,
        PeptideRegistry.lab_id.is_(lab_id) if lab_id is None else PeptideRegistry.lab_id == lab_id,
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        row = PeptideRegistry(lab_id=lab_id, sequence=sequence)
        db.add(row)
        db.flush()
    return row


def touch_selected(db: Session, sequence: str, lab_id: int | None = None) -> None:
    row = _registry_row(db, sequence, lab_id)
    row.times_selected += 1
    row.last_selected_at = _utcnow()


def touch_tested(db: Session, sequence: str, outcome: str, lab_id: int | None = None) -> None:
    """Record a wet-lab result against the registry, keeping the best outcome seen."""
    row = _registry_row(db, sequence, lab_id)
    row.times_tested += 1
    row.last_tested_at = _utcnow()
    current = OUTCOME_RANK.get(row.best_outcome or "", -1)
    if OUTCOME_RANK.get(outcome, -1) > current:
        row.best_outcome = outcome


def tested_sequences(db: Session, lab_id: int | None = None) -> dict[str, PeptideRegistry]:
    """Everything this lab has already tested, keyed by sequence.

    One indexed query — the selector calls this on every run.
    """
    stmt = sa_select(PeptideRegistry).where(PeptideRegistry.times_tested > 0)
    if lab_id is not None:
        stmt = stmt.where(PeptideRegistry.lab_id == lab_id)
    return {r.sequence: r for r in db.execute(stmt).scalars().all()}
