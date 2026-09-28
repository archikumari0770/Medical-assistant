"""
Medication safety checks against the patient's active medication list:
  - drug-drug interactions among current meds
  - contraindications between current meds and candidate conditions
"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.database.postgres import AsyncSessionLocal
from app.graph.queries import contraindications_for_medications, interactions_between
from app.models.analysis import CandidateCondition, SafetyFlag
from app.models.patient import MedicationRecord


async def _active_medication_names(patient_id: str) -> list[str]:
    async with AsyncSessionLocal() as db:
        result = await db.scalars(
            select(MedicationRecord).where(
                MedicationRecord.patient_id == uuid.UUID(patient_id),
                MedicationRecord.active.is_(True),
            )
        )
        return [m.name for m in result.all()]


async def check_medication_safety(patient_id: str, candidates: list[CandidateCondition]) -> list[SafetyFlag]:
    flags: list[SafetyFlag] = []
    active_meds = await _active_medication_names(patient_id)
    if not active_meds:
        return flags

    interactions = await interactions_between(active_meds)
    for interaction in interactions:
        severity = "critical" if interaction.get("severity") == "major" else "warning"
        flags.append(
            SafetyFlag(
                severity=severity,
                message=f"Potential interaction between {interaction['medication_a']} and {interaction['medication_b']}.",
                triggered_by=f"{interaction['medication_a']} + {interaction['medication_b']}",
            )
        )

    contraindications = await contraindications_for_medications(active_meds)
    candidate_names = {c.name.lower() for c in candidates}
    for contra in contraindications:
        if contra["condition_name"].lower() in candidate_names:
            flags.append(
                SafetyFlag(
                    severity="warning",
                    message=f"{contra['medication']} is contraindicated for {contra['condition_name']}, "
                            f"a current candidate condition.",
                    triggered_by=contra["medication"],
                )
            )

    return flags
