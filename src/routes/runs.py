"""Phase 6b — run persistence and history.

Every shortlist the system produces is saved and can be reopened with identical
numbers. The scores stored are the ones shown at the time, frozen; retraining a model
must never silently rewrite a shortlist a scientist already acted on.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import crud
from db import get_db
from schemas import RunDetail, RunItemOut, RunLabelUpdate, RunSummary

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunSummary])
def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    project_id: int | None = None,
    scientist_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Saved runs, newest first."""
    return crud.list_runs(db, limit=limit, project_id=project_id, scientist_id=scientist_id)


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Reopen a saved shortlist exactly as it was."""
    run = crud.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    return RunDetail(
        id=run.id, species=run.species, k=run.k, theta=run.theta, logdet=run.logdet,
        pool_size=run.pool_size, n_items=len(run.items), n_excluded=run.n_excluded,
        label=run.label, project_id=run.project_id, scientist_id=run.scientist_id,
        scientist_name=None, created_at=run.created_at,
        items=[RunItemOut.model_validate(i) for i in run.items],
    )


@router.patch("/{run_id}", response_model=RunSummary)
def label_run(run_id: int, body: RunLabelUpdate, db: Session = Depends(get_db)):
    """Name a run so it is findable later ('round 2, after the charge tweak')."""
    run = crud.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    run.label = body.label
    db.commit()
    db.refresh(run)
    return RunSummary(
        id=run.id, species=run.species, k=run.k, theta=run.theta, logdet=run.logdet,
        pool_size=run.pool_size, n_items=len(run.items), n_excluded=run.n_excluded,
        label=run.label, project_id=run.project_id, scientist_id=run.scientist_id,
        scientist_name=None, created_at=run.created_at,
    )


@router.delete("/{run_id}")
def delete_run(run_id: int, db: Session = Depends(get_db)):
    if not crud.delete_run(db, run_id):
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    return {"deleted": run_id}
