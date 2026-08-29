"""Database engine and session management.

SQLite via SQLAlchemy 2.0, file at data/pharmamind.db.

SQLite deliberately, not Postgres: a database that needs a running service is a live
failure mode at a demo venue. Because everything goes through SQLAlchemy, moving to
Postgres later is a connection-string change and nothing else.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import config as C

DB_PATH = C.DATA / "pharmamind.db"
DATABASE_URL = os.getenv("PHARMAMIND_DB_URL", f"sqlite:///{DB_PATH}")

# check_same_thread=False because FastAPI serves requests from a threadpool.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record):
    """Foreign keys are OFF by default in SQLite, which would silently allow orphans."""
    if DATABASE_URL.startswith("sqlite"):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")  # concurrent reads while writing
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency. Yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create every table that does not exist yet.

    No Alembic. The schema is frozen by design (see docs/07-system-design.md) and there
    is exactly one SQLite file, so there is no migration path to manage. If the schema
    ever needs to evolve across deployments, add Alembic then -- not before.
    """
    from models_db import Base  # imported here to avoid a circular import

    C.DATA.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    """Drop and recreate everything. Development and seeding only."""
    from models_db import Base

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
