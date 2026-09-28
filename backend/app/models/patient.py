"""
Patient data model — ORM tables + Pydantic schemas.

NOTE: this project targets synthetic/de-identified data only (see project
README). If adapted to real patient data, add field-level encryption,
access-control, and audit logging appropriate to your jurisdiction's
health-data regulations before storing anything.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field
from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


# ---------------------------------------------------------------- ORM ----

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str] = mapped_column(String(128))
    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_archived: Mapped[bool] = mapped_column(default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    encounters: Mapped[list["Encounter"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    medications: Mapped[list["MedicationRecord"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"))
    encounter_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    chief_complaint: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")

    patient: Mapped[Patient] = relationship(back_populates="encounters")


class MedicationRecord(Base):
    __tablename__ = "medication_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"))
    name: Mapped[str] = mapped_column(String(256))
    dosage: Mapped[str] = mapped_column(String(128), default="")
    started_at: Mapped[date] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(default=True)

    patient: Mapped[Patient] = relationship(back_populates="medications")


# ----------------------------------------------------------- Schemas ----

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str


class PatientOut(BaseModel):
    id: uuid.UUID
    external_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    is_archived: bool
    archived_at: datetime | None

    model_config = {"from_attributes": True}


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    sex: str | None = None


class EncounterCreate(BaseModel):
    chief_complaint: str
    notes: str = ""


class EncounterOut(BaseModel):
    id: uuid.UUID
    encounter_date: datetime
    chief_complaint: str
    notes: str

    model_config = {"from_attributes": True}


class MedicationCreate(BaseModel):
    name: str
    dosage: str = ""
    started_at: date
    ended_at: date | None = None
    active: bool = True


class MedicationOut(BaseModel):
    id: uuid.UUID
    name: str
    dosage: str
    started_at: date
    ended_at: date | None
    active: bool

    model_config = {"from_attributes": True}