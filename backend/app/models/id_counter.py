"""
Generic named counters used to generate system-assigned IDs (patient
IDs, staff IDs) — see app/utils/id_generator.py.

This is a brand-new table, which matters: it means adding this feature
doesn't require an ALTER TABLE on any table you already have — Postgres
tables that don't exist yet get created automatically the next time you
run `python -m scripts.init_postgres`.
"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.postgres import Base


class IdCounter(Base):
    __tablename__ = "id_counters"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[int] = mapped_column(default=0)