"""Shared pydantic request/response models for phases 6-9 — FROZEN alongside models_db.

Part of the phase 6a contract. Add new models freely; do not change the shape of an
existing one without announcing it, because another track is building against it.

Naming rule carried over from the existing API: display `q_i`, never `q_i_scaled`.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- runs and history (phase 6b, the engine track) ---------------------------------

class RunItemOut(ORMModel):
    rank: int
    sequence: str
    q_i: float
    p_active: float
    p_toxic: float
    similarity_to_nearest: float
    marginal_log_gain: float
    is_diversity_pick: bool


class RunSummary(ORMModel):
    """One row in the history list. Deliberately excludes items — keep the list light."""
    id: int
    species: str
    k: int
    theta: float
    logdet: float
    pool_size: int
    n_items: int = 0
    n_excluded: int = 0
    label: str | None = None
    project_id: int | None = None
    scientist_id: int | None = None
    scientist_name: str | None = None
    created_at: datetime


class RunDetail(RunSummary):
    items: list[RunItemOut] = Field(default_factory=list)


class RunLabelUpdate(BaseModel):
    label: str = Field(..., max_length=200)


# --- auth and people (phase 7, the product track) -----------------------------------------

class ScientistOut(ORMModel):
    """Never carries password_hash. Do not add it."""
    id: int
    lab_id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=8, max_length=128)
    lab_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    scientist: ScientistOut


class LabOut(ORMModel):
    id: int
    name: str
    created_at: datetime


# --- projects (phase 7, the product track) --------------------------------------------------

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    target_species: str
    status: str = "active"


class ProjectOut(ORMModel):
    id: int
    lab_id: int
    name: str
    target_species: str
    status: str
    created_by: int | None = None
    is_seeded: bool = False
    created_at: datetime
    n_runs: int = 0
    n_members: int = 0


class ProjectMemberAdd(BaseModel):
    scientist_id: int
    role: str = "scientist"


# --- experiments and lab memory (phase 8, the engine track) -----------------------------

class ExperimentCreate(BaseModel):
    sequence: str
    assay: str = Field(..., pattern="^(MIC|hemolysis)$")
    outcome: str = Field(..., pattern="^(hit|miss|toxic|inconclusive)$")
    measured_value: float | None = None
    unit: str | None = None
    project_id: int | None = None
    run_item_id: int | None = None
    notes: str | None = None


class ExperimentOut(ORMModel):
    id: int
    sequence: str
    assay: str
    outcome: str
    measured_value: float | None
    unit: str | None
    source: str
    project_id: int | None
    scientist_id: int | None
    notes: str | None
    tested_at: datetime


class RegistryEntry(ORMModel):
    sequence: str
    times_selected: int
    times_tested: int
    best_outcome: str | None
    last_tested_at: datetime | None


class LabMemorySummary(BaseModel):
    """What the shortlist screen shows about what was skipped and why."""
    n_known: int
    n_excluded: int
    excluded: list[RegistryEntry] = Field(default_factory=list)


# --- analytics (phase 9) -------------------------------------------------------------

class CalibrationBucket(BaseModel):
    predicted_lower: float
    predicted_upper: float
    n: int
    observed_hit_rate: float | None


class RoundStat(BaseModel):
    run_id: int
    created_at: datetime
    n_tested: int
    n_hits: int
    hit_rate: float | None


class AnalyticsOut(BaseModel):
    project_id: int | None
    n_runs: int
    n_experiments: int
    overall_hit_rate: float | None
    calibration: list[CalibrationBucket] = Field(default_factory=list)
    rounds: list[RoundStat] = Field(default_factory=list)
    cumulative_chemotypes: list[int] = Field(default_factory=list)
