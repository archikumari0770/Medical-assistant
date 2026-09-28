from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.audit.logger import record_analysis_run
from app.auth.dependencies import require_roles
from app.decision.candidate_generator import generate_candidates
from app.decision.conflicts import annotate_conflicts
from app.decision.scorer import score_candidates
from app.llm.narrator import summarize_analysis
from app.models.analysis import AnalysisRequest, AnalysisResult
from app.models.user import User, UserRole
from app.nlp.extractor import extract_symptoms
from app.safety.medication_safety import check_medication_safety
from app.safety.red_flags import check_red_flags

router = APIRouter()


@router.post("", response_model=AnalysisResult)
async def run_analysis(
    payload: AnalysisRequest,
    user: User = Depends(require_roles(UserRole.doctor)),
):
    """
    Main decision-support pipeline:

    1. Extract/normalize symptoms (from structured input + free text).
    2. Generate candidate conditions from the knowledge graph + patient RAG.
    3. Score and annotate conflicts/uncertainty for each candidate.
    4. Run safety checks (red flags, medication interactions).
    5. Produce a narrative summary via the LLM layer.
    """
    symptoms = list(payload.symptoms)
    if payload.free_text:
        symptoms += await extract_symptoms(payload.free_text)

    if not symptoms:
        raise HTTPException(400, "No symptoms provided or extracted")

    candidates = await generate_candidates(patient_id=str(payload.patient_id), symptoms=symptoms)
    candidates = await score_candidates(candidates, patient_id=str(payload.patient_id))
    candidates = await annotate_conflicts(candidates, patient_id=str(payload.patient_id))

    safety_flags = []
    safety_flags += await check_red_flags(symptoms=symptoms)
    safety_flags += await check_medication_safety(patient_id=str(payload.patient_id), candidates=candidates)

    result = AnalysisResult(
        patient_id=payload.patient_id,
        candidates=candidates,
        safety_flags=safety_flags,
    )
    result.narrative_summary = await summarize_analysis(result)
    await record_analysis_run(result, requested_by=user.email)
    return result
