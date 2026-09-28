"""
Seeds one synthetic demo patient end-to-end: Postgres record, a sample
encounter, an active medication, and an indexed free-text note in Qdrant.

Run from backend/ (after docker compose up and init_postgres/seed_neo4j):
    python -m scripts.seed_demo
"""
import asyncio
from datetime import date

from app.database.postgres import AsyncSessionLocal, init_postgres
from app.database.qdrant import ensure_collections
from app.models.patient import Encounter, MedicationRecord, Patient
from app.rag.patient_rag import index_patient_document
from app.utils.id_generator import next_sequential_id

SAMPLE_NOTE = """
Patient presents with fever and cough for 3 days, denies shortness of breath.
No history of chest pain. Reports mild fatigue. Ruled out pneumonia on prior
chest X-ray six months ago for a similar presentation.
"""


async def seed():
    await init_postgres()
    await ensure_collections()

    async with AsyncSessionLocal() as db:
        external_id = await next_sequential_id(db, counter_name="patient", prefix="PT")
        patient = Patient(
            external_id=external_id,
            first_name="Jordan",
            last_name="Rivera",
            date_of_birth=date(1988, 4, 12),
            sex="unspecified",
        )
        db.add(patient)
        await db.flush()  # get patient.id before commit

        db.add(
            Encounter(
                patient_id=patient.id,
                chief_complaint="Fever and cough for 3 days",
                notes=SAMPLE_NOTE.strip(),
            )
        )
        db.add(
            MedicationRecord(
                patient_id=patient.id,
                name="Lisinopril",
                dosage="10mg daily",
                started_at=date(2023, 1, 1),
                active=True,
            )
        )
        await db.commit()
        await db.refresh(patient)

        doc_id = await index_patient_document(
            patient_id=str(patient.id),
            title="Initial visit note",
            text=SAMPLE_NOTE.strip(),
        )

        print(f"Created demo patient {patient.id} (external_id={external_id})")
        print(f"Indexed document {doc_id} into Qdrant")


if __name__ == "__main__":
    asyncio.run(seed())