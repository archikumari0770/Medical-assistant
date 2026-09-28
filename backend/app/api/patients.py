from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.database.postgres import get_db
from app.models.lab import LabResult
from app.models.patient import (
    Encounter,
    EncounterCreate,
    EncounterOut,
    MedicationCreate,
    MedicationOut,
    MedicationRecord,
    Patient,
    PatientCreate,
    PatientOut,
    PatientUpdate,
)
from app.models.user import User, UserRole
from app.rag.patient_rag import patient_has_indexed_documents
from app.utils.id_generator import next_sequential_id

router = APIRouter()

# Demographics: front desk registers/looks up patients; doctors need this
# too; lab staff need it to attach results to the right patient; admin
# needs it to manage (archive/restore/delete) records.
_READ_DEMOGRAPHICS = (UserRole.receptionist, UserRole.doctor, UserRole.lab, UserRole.admin)
_WRITE_DEMOGRAPHICS = (UserRole.receptionist, UserRole.doctor)
# Clinical content (encounters, medications): doctor only.
_CLINICAL = (UserRole.doctor,)


@router.post("", response_model=PatientOut, status_code=201)
async def create_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*_WRITE_DEMOGRAPHICS)),
):
    external_id = await next_sequential_id(db, counter_name="patient", prefix="PT")
    patient = Patient(external_id=external_id, **payload.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("", response_model=list[PatientOut])
async def list_patients(
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    include_archived: bool = False,
    user: User = Depends(require_roles(*_READ_DEMOGRAPHICS)),
):
    stmt = select(Patient)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Patient.last_name.ilike(like) | Patient.first_name.ilike(like))
    # Only admin can ever see archived patients, and only when they ask for them.
    if not (user.role == UserRole.admin and include_archived):
        stmt = stmt.where(Patient.is_archived.is_(False))
    result = await db.scalars(stmt.order_by(Patient.last_name).limit(50))
    return result.all()


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*_READ_DEMOGRAPHICS)),
):
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    # Archived patients are invisible to everyone except admin, even by direct ID.
    if patient.is_archived and user.role != UserRole.admin:
        raise HTTPException(404, "Patient not found")
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*_WRITE_DEMOGRAPHICS)),
):
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    if patient.is_archived:
        raise HTTPException(409, "This patient is archived — restore the record before editing it.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)
    return patient


@router.patch("/{patient_id}/archive", response_model=PatientOut)
async def archive_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    """Hides a patient from active use without deleting anything. This is
    the recommended way to 'remove' a patient — clinical history, audit
    trail, and referential integrity all stay intact and reversible."""
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    patient.is_archived = True
    patient.archived_at = datetime.utcnow()
    await db.commit()
    await db.refresh(patient)
    return patient


@router.patch("/{patient_id}/restore", response_model=PatientOut)
async def restore_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    patient.is_archived = False
    patient.archived_at = None
    await db.commit()
    await db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    """
    Permanently deletes a patient — only permitted when the record is
    genuinely empty (no encounters, medications, lab results, or indexed
    notes). This exists for cleaning up accidental duplicate registrations,
    not for removing real patient history — use archive for that instead.
    """
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")

    encounter_count = await db.scalar(
        select(func.count()).select_from(Encounter).where(Encounter.patient_id == patient_id)
    )
    medication_count = await db.scalar(
        select(func.count()).select_from(MedicationRecord).where(MedicationRecord.patient_id == patient_id)
    )
    lab_count = await db.scalar(
        select(func.count()).select_from(LabResult).where(LabResult.patient_id == patient_id)
    )
    has_documents = await patient_has_indexed_documents(str(patient_id))

    if encounter_count or medication_count or lab_count or has_documents:
        raise HTTPException(
            409,
            "This patient has clinical history on file and can't be permanently deleted. "
            "Archive the record instead.",
        )

    await db.delete(patient)
    await db.commit()
    return None


@router.post("/{patient_id}/encounters", response_model=EncounterOut, status_code=201)
async def add_encounter(
    patient_id: uuid.UUID,
    payload: EncounterCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*_CLINICAL)),
):
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    encounter = Encounter(patient_id=patient_id, **payload.model_dump())
    db.add(encounter)
    await db.commit()
    await db.refresh(encounter)
    return encounter


@router.get("/{patient_id}/encounters", response_model=list[EncounterOut])
async def list_encounters(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*_CLINICAL)),
):
    result = await db.scalars(
        select(Encounter).where(Encounter.patient_id == patient_id).order_by(Encounter.encounter_date.desc())
    )
    return result.all()


@router.post("/{patient_id}/medications", response_model=MedicationOut, status_code=201)
async def add_medication(
    patient_id: uuid.UUID,
    payload: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*_CLINICAL)),
):
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    med = MedicationRecord(patient_id=patient_id, **payload.model_dump())
    db.add(med)
    await db.commit()
    await db.refresh(med)
    return med


@router.get("/{patient_id}/medications", response_model=list[MedicationOut])
async def list_medications(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*_CLINICAL)),
):
    result = await db.scalars(select(MedicationRecord).where(MedicationRecord.patient_id == patient_id))
    return result.all()