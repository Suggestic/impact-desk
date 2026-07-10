"""Aggregator package: the vendor-agnostic data seam.

Import `AggregatorClient` for typing, and `get_client()` to obtain the
configured implementation. No concrete vendor is hardcoded anywhere — selection
is by name (env `AGGREGATOR`, default "mock").
"""

from __future__ import annotations

import os
from typing import Optional

from .base import (
    AggregatedPost,
    AggregatedProfile,
    AggregatorClient,
    ProfileNotFound,
)
from .csv_adapter import CSVAggregatorClient
from .mock import MockAggregatorClient

__all__ = [
    "AggregatorClient",
    "AggregatedProfile",
    "AggregatedPost",
    "ProfileNotFound",
    "MockAggregatorClient",
    "CSVAggregatorClient",
    "get_client",
]


def get_client(name: Optional[str] = None, **kwargs) -> AggregatorClient:
    """Return an aggregator client by name.

    - "mock" (default): runnable with no vendor or key.
    - "csv":  requires `csv_path=...` (or pass a prebuilt client directly).

    A real paid vendor becomes a new adapter + a new branch here; callers are
    unaffected.
    """
    name = (name or os.environ.get("AGGREGATOR", "mock")).lower()
    if name == "mock":
        return MockAggregatorClient()
    if name == "csv":
        csv_path = kwargs.get("csv_path") or os.environ.get("AGGREGATOR_CSV_PATH")
        if not csv_path:
            raise ValueError("csv aggregator requires csv_path / AGGREGATOR_CSV_PATH")
        return CSVAggregatorClient.from_path(csv_path)
    raise ValueError(f"unknown aggregator '{name}' (known: mock, csv)")
