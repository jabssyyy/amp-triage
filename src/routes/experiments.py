"""Phase 8 — experimental results and institutional memory.

This is the phase that makes the database worth having.

The diversity objective already avoids redundancy *inside* one batch of twenty. Backed
by a record of everything the lab has already tested, it avoids redundancy *across the
lab's entire history*. Scientist 2 stops being handed peptides from a scaffold that
scientist 1 already proved dead three weeks ago on a different pathogen.

Same submodular argument, extended along the time axis. The pitch line it earns is
"we never spend your money learning the same thing twice."

Note on where the exclusion happens: in this router, NOT in select.py. The selection
engine is verified against brute force with 24 passing checks and its signatures are
frozen. Filtering the pool before it reaches the engine gets the same result without
touching any of that.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

import crud
from auth import get_current_user_optional
from db import get_db
from models_db import Experiment, PeptideRegistry, RunItem, Scientist
from schemas import ExperimentCreate, ExperimentOut, LabMemorySummary, RegistryEntry

router = APIRouter(tags=["experiments"])


def _lab_id_of(user) -> int | None:
    return getattr(user, "lab_id", None)


@router.post("/experiments", response_model=ExperimentOut)
def record_experiment(
    body: ExperimentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """Record a wet-lab outcome for a peptide and update the lab's memory.

    `source` is forced to 'wet_lab' here — only the seeder may write 'seeded_public',
    so a demonstration record can never be created through the product and later be
    mistaken for the lab's own work.
    """
    sequence = body.sequence.strip().upper()
    if not sequence:
        raise HTTPException(status_code=400, detail="sequence is required")

    exp = Experiment(
        project_id=body.project_id,
        run_item_id=body.run_item_id,
        scientist_id=getattr(current_user, "id", None),
        sequence=sequence,
        assay=body.assay,
        measured_value=body.measured_value,
        unit=body.unit,
        outcome=body.outcome,
        source="wet_lab",
        notes=body.notes,
    )
    db.add(exp)

    crud.touch_tested(db, sequence, body.outcome, lab_id=_lab_id_of(current_user))

    # advance the assignment if this result came from a shortlisted candidate
    if body.run_item_id is not None:
        item = db.get(RunItem, body.run_item_id)
        if item is not None and item.assignment is not None:
            item.assignment.status = "tested"

    db.commit()
    db.refresh(exp)
    return exp


@router.get("/experiments", response_model=list[ExperimentOut])
def list_experiments(
    project_id: int | None = None,
    sequence: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = sa_select(Experiment).order_by(Experiment.tested_at.desc()).limit(limit)
    if project_id is not None:
        stmt = stmt.where(Experiment.project_id == project_id)
    if sequence:
        stmt = stmt.where(Experiment.sequence == sequence.strip().upper())
    return list(db.execute(stmt).scalars().all())


@router.delete("/experiments/{experiment_id}")
def delete_experiment(experiment_id: int, db: Session = Depends(get_db)):
    exp = db.get(Experiment, experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"experiment {experiment_id} not found")
    db.delete(exp)
    db.commit()
    return {"deleted": experiment_id}


@router.get("/lab-memory", response_model=LabMemorySummary)
def lab_memory(
    sequences: str | None = Query(default=None, description="Comma-separated pool to check"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """What does this lab already know about these peptides?

    Called by the shortlist screen so it can say "12 candidates skipped: already tested
    by this lab" and show which ones.
    """
    known = crud.tested_sequences(db, lab_id=_lab_id_of(current_user))
    if sequences:
        pool = {s.strip().upper() for s in sequences.split(",") if s.strip()}
        hits = {s: r for s, r in known.items() if s in pool}
    else:
        hits = known
    entries = [RegistryEntry.model_validate(r) for r in hits.values()]
    entries.sort(key=lambda e: (e.last_tested_at is None, e.last_tested_at), reverse=True)
    return LabMemorySummary(n_known=len(known), n_excluded=len(entries), excluded=entries)


@router.get("/registry", response_model=list[RegistryEntry])
def registry(
    limit: int = Query(default=200, ge=1, le=1000),
    tested_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """The lab's accumulated peptide memory."""
    lab_id = _lab_id_of(current_user)
    stmt = sa_select(PeptideRegistry)
    if lab_id is not None:
        stmt = stmt.where(PeptideRegistry.lab_id == lab_id)
    if tested_only:
        stmt = stmt.where(PeptideRegistry.times_tested > 0)
    stmt = stmt.order_by(PeptideRegistry.last_tested_at.desc().nullslast()).limit(limit)
    return list(db.execute(stmt).scalars().all())
