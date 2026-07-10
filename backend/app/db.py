"""Database engine / session setup.

Defaults to SQLite for the prototype and switches to Postgres (Supabase) purely
via the DATABASE_URL env var — no code change required.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables. For the prototype this stands in for real migrations;
    swap for Alembic when moving to Supabase."""
    from . import models  # noqa: F401  (register mappers)

    Base.metadata.create_all(bind=engine)
