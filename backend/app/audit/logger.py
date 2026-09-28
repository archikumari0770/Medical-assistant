"""
Audit trail for decision-support runs. Any real deployment handling
health data should persist these records durably (append-only table,
write-once storage) and restrict access — this starter version logs
via loguru and is NOT a substitute for a compliant audit store.
"""
from __future__ import annotations

from loguru import logger

from app.models.analysis import AnalysisResult


async def record_analysis_run(result: AnalysisResult, requested_by: str = "unknown") -> None:
    logger.bind(audit=True).info(
        "analysis_run",
        analysis_id=str(result.id),
        patient_id=str(result.patient_id),
        requested_by=requested_by,
        candidate_count=len(result.candidates),
        safety_flag_count=len(result.safety_flags),
        top_candidate=result.candidates[0].name if result.candidates else None,
    )
