"""Aggregator — importing this module registers every model on `Base.metadata`.

Alembic's env.py imports from here so autogenerate / upgrade sees the full
schema. Each domain owns its own `models.py`; this file only re-exports.
"""

from __future__ import annotations

