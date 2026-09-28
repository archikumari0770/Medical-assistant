from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.database.postgres import get_db
from app.models.lab import LabResult, LabResultCreate, LabResultOut
from app.models.patient import Patient
from app.models.user import User, UserRole

router = APIRouter()


@router.post("", response_model=LabResultOut, status_code=201)
async def add_lab_result(
    payload: LabResultCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.lab)),
):
    patient = await db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")

    result = LabResult(**payload.model_dump(), entered_by=user.email)
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result


@router.get("/patient/{patient_id}", response_model=list[LabResultOut])
async def list_lab_results_for_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.lab, UserRole.doctor)),
):
    result = await db.scalars(
        select(LabResult).where(LabResult.patient_id == patient_id).order_by(LabResult.resulted_at.desc())
    )
    return result.all()


@router.get("/recent", response_model=list[LabResultOut])
async def list_recent_lab_results(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.lab)),
    limit: int = 25,
):
    """Recent-activity queue for the lab role's landing page."""
    result = await db.scalars(select(LabResult).order_by(LabResult.resulted_at.desc()).limit(limit))
    return result.all()
