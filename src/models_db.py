"""The complete database schema — FROZEN.

This file is the shared contract between three tracks building in parallel
(phase 6b persistence, phase 7 auth, phase 8 institutional memory). Every table any
of those phases needs is defined here, up front, so nobody has to add one mid-flight.

DO NOT add, rename or alter a column without announcing it. A silent schema change
breaks the other tracks in ways that do not surface until merge.

Two design points worth understanding before you use these tables:

1. RunItem stores the scores AS THEY WERE at selection time. Models get retrained; a
   shortlist is the historical record of a decision somebody acted on and must never
   change underneath them. It is also what makes calibration analysis possible later.

2. PeptideRegistry is denormalised on purpose — one row per (lab, sequence). The
   selector reads it on every run, so the "has this lab already tested this peptide?"
   lookup has to be one indexed hit, not a join across all history.

Nullability note: run.project_id and run.scientist_id are NULLABLE. Phase 6b persists
runs before authentication exists (phase 7), and the anonymous demo path has to keep
working after it exists. Attribution is an enrichment, not a requirement.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# --- organisation and people --------------------------------------------------

class Lab(Base):
    __tablename__ = "lab"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    scientists: Mapped[list["Scientist"]] = relationship(back_populates="lab")
    projects: Mapped[list["Project"]] = relationship(back_populates="lab")


class Scientist(Base):
    __tablename__ = "scientist"

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey("lab.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # bcrypt hash. Never return this from an endpoint, never log it.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="scientist", nullable=False)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    lab: Mapped["Lab"] = relationship(back_populates="scientists")


# --- campaigns ------------------------------------------------------------------

class Project(Base):
    """A campaign against one pathogen. The unit of work a scientist owns."""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey("lab.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # exactly one target, drawn from config.PRIORITY_SPECIES
    target_species: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("scientist.id"), nullable=True)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    lab: Mapped["Lab"] = relationship(back_populates="projects")
    runs: Mapped[list["Run"]] = relationship(back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_member"
    __table_args__ = (UniqueConstraint("project_id", "scientist_id", name="uq_project_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    scientist_id: Mapped[int] = mapped_column(ForeignKey("scientist.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="scientist", nullable=False)


# --- candidate pools -------------------------------------------------------------

class Pool(Base):
    __tablename__ = "pool"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    n_sequences: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("scientist.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    sequences: Mapped[list["PoolSequence"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan"
    )


class PoolSequence(Base):
    __tablename__ = "pool_sequence"
    __table_args__ = (Index("ix_pool_sequence_seq", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pool_id: Mapped[int] = mapped_column(ForeignKey("pool.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[str] = mapped_column(String(500), nullable=False)

    pool: Mapped["Pool"] = relationship(back_populates="sequences")


# --- selection runs ---------------------------------------------------------------

class Run(Base):
    """One selection: a pool plus species, k and theta, producing a ranked shortlist."""

    __tablename__ = "run"

    id: Mapped[int] = mapped_column(primary_key=True)
    # nullable: runs are persisted before auth exists, and the anonymous demo path
    # must keep working after it does
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="SET NULL"), nullable=True)
    pool_id: Mapped[int | None] = mapped_column(ForeignKey("pool.id", ondelete="SET NULL"), nullable=True)
    scientist_id: Mapped[int | None] = mapped_column(ForeignKey("scientist.id", ondelete="SET NULL"), nullable=True)

    species: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    k: Mapped[int] = mapped_column(Integer, nullable=False)
    theta: Mapped[float] = mapped_column(Float, nullable=False)
    logdet: Mapped[float] = mapped_column(Float, nullable=False)
    pool_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # phase 8: institutional memory
    excluded_tested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    n_excluded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)

    project: Mapped["Project | None"] = relationship(back_populates="runs")
    items: Mapped[list["RunItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunItem.rank"
    )


class RunItem(Base):
    """One selected peptide, with its scores frozen at selection time."""

    __tablename__ = "run_item"
    __table_args__ = (Index("ix_run_item_sequence", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[str] = mapped_column(String(500), nullable=False)

    q_i: Mapped[float] = mapped_column(Float, nullable=False)
    p_active: Mapped[float] = mapped_column(Float, nullable=False)
    p_toxic: Mapped[float] = mapped_column(Float, nullable=False)
    similarity_to_nearest: Mapped[float] = mapped_column(Float, nullable=False)
    marginal_log_gain: Mapped[float] = mapped_column(Float, nullable=False)
    # true when top-N would not have picked this one
    is_diversity_pick: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="items")
    assignment: Mapped["Assignment | None"] = relationship(
        back_populates="run_item", cascade="all, delete-orphan", uselist=False
    )


class Assignment(Base):
    """Which scientist owns taking this candidate through synthesis and testing."""

    __tablename__ = "assignment"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_item_id: Mapped[int] = mapped_column(ForeignKey("run_item.id", ondelete="CASCADE"), nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("scientist.id", ondelete="SET NULL"), nullable=True)
    # proposed | assigned | synthesised | tested | dropped
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    run_item: Mapped["RunItem"] = relationship(back_populates="assignment")


# --- experimental results ------------------------------------------------------------

class Experiment(Base):
    """A wet-lab outcome for one peptide.

    `source` is load-bearing. Seeded demonstration rows drawn from public DBAASP records
    must never be presentable as this lab's own wet-lab work, and the UI reads this column
    to say so. Presenting public data as in-house results would be the same class of
    mistake as a fabricated citation.
    """

    __tablename__ = "experiment"
    __table_args__ = (Index("ix_experiment_sequence", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="SET NULL"), nullable=True)
    run_item_id: Mapped[int | None] = mapped_column(ForeignKey("run_item.id", ondelete="SET NULL"), nullable=True)
    scientist_id: Mapped[int | None] = mapped_column(ForeignKey("scientist.id", ondelete="SET NULL"), nullable=True)

    sequence: Mapped[str] = mapped_column(String(500), nullable=False)
    assay: Mapped[str] = mapped_column(String(30), nullable=False)          # MIC | hemolysis
    measured_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)        # hit | miss | toxic | inconclusive
    # wet_lab | seeded_public  -- never blur these two
    source: Mapped[str] = mapped_column(String(20), default="wet_lab", nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)


class PeptideRegistry(Base):
    """Lab-wide memory: every peptide this lab has selected or tested.

    Read by the selector on every run, so keep it one indexed lookup.
    """

    __tablename__ = "peptide_registry"
    __table_args__ = (UniqueConstraint("lab_id", "sequence", name="uq_registry_lab_sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_id: Mapped[int | None] = mapped_column(ForeignKey("lab.id", ondelete="CASCADE"), nullable=True, index=True)
    sequence: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    times_selected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    times_tested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # best outcome ever observed: hit > inconclusive > miss > toxic
    best_outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_selected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# Ranking used when collapsing several experiments into one registry verdict.
OUTCOME_RANK = {"hit": 3, "inconclusive": 2, "miss": 1, "toxic": 0}
