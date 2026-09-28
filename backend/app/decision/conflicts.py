"""
Annotates each candidate with conflicting evidence drawn from the
patient's own record (e.g. a prior note explicitly ruling out a
condition) and flags candidates whose evidence is thin/uncertain.
"""
from __future__ import annotations

from app.models.analysis import CandidateCondition, EvidenceItem
from app.rag.patient_rag import search_patient_documents


async def annotate_conflicts(candidates: list[CandidateCondition], patient_id: str) -> list[CandidateCondition]:
    for candidate in candidates:
        # Look for patient-history notes that might contradict this candidate
        # (e.g. "ruled out X", "X negative", prior negative workup).
        hits = await search_patient_documents(
            patient_id=patient_id,
            query=f"ruled out negative history of {candidate.name}",
            top_k=3,
        )
        for hit in hits:
            text = hit.get("text", "")
            lowered = text.lower()
            if "ruled out" in lowered or "negative for" in lowered or "denies" in lowered:
                if candidate.name.lower() in lowered:
                    candidate.conflicting_evidence.append(
                        EvidenceItem(
                            source="patient_history",
                            description=text[:280],
                            reference_id=str(hit.get("id")),
                        )
                    )

        if len(candidate.supporting_evidence) <= 1:
            candidate.uncertainty_notes = (
                "Limited evidence — based on a single symptom match or source. "
                "Consider additional history, exam findings, or testing."
            )
        elif candidate.conflicting_evidence:
            candidate.uncertainty_notes = (
                "Conflicting evidence found in patient history — review flagged notes before considering."
            )

    return candidates
