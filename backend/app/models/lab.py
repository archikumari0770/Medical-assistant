"""
Lab result records — entered by the 'lab' role, read by the 'doctor' role.
Kept as its own table/router (rather than folded into MedicationRecord or
Encounter) since lab staff have a distinct workflow: they enter results
against a patient without needing access to that patient's clinical notes,
medications, or the diagnosis pipeline.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.postgres import Base


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"))
    test_name: Mapped[str] = mapped_column(String(256))
    result_value: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(32), default="")
    reference_range: Mapped[str] = mapped_column(String(64), default="")
    entered_by: Mapped[str] = mapped_column(String(256), default="")  # lab user's email, for traceability
    resulted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LabResultCreate(BaseModel):
    patient_id: uuid.UUID
    test_name: str
    result_value: str
    unit: str = ""
    reference_range: str = ""


class LabResultOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    test_name: str
    result_value: str
    unit: str
    reference_range: str
    entered_by: str
    resulted_at: datetime

    model_config = {"from_attributes": True}
