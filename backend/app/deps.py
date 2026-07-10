"""Shared FastAPI dependencies: DB session and the operator/client role gate.

Auth is deliberately minimal (§6): enough to separate the operator (read/write)
from read-only clients, not enterprise SSO. An operator presents a bearer token
matching `OPERATOR_TOKEN`; everyone else is treated as a read-only client.
Swap this for real auth (e.g. Supabase Auth / JWT) without touching endpoints.
"""

from __future__ import annotations

import os
from typing import Iterator, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db import SessionLocal

OPERATOR_TOKEN = os.environ.get("OPERATOR_TOKEN", "dev-operator-token")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_role(authorization: Optional[str] = Header(default=None)) -> str:
    """Return 'operator' for a valid bearer token, else 'client'."""
    if authorization and authorization.removeprefix("Bearer ").strip() == OPERATOR_TOKEN:
        return "operator"
    return "client"


def require_operator(role: str = Depends(get_role)) -> str:
    if role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator access required.",
        )
    return role
