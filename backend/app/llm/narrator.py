"""
Produces the final narrative_summary field on an AnalysisResult by
calling the LLM with the structured pipeline output as context.
"""
from __future__ import annotations

from loguru import logger

from app.llm.client import complete
from app.llm.prompt import NARRATOR_SYSTEM_PROMPT, build_narrator_prompt
from app.models.analysis import AnalysisResult


async def summarize_analysis(result: AnalysisResult) -> str:
    if not result.candidates and not result.safety_flags:
        return "No candidate conditions or safety flags generated for the given input."

    prompt = build_narrator_prompt(result)
    try:
        return await complete(NARRATOR_SYSTEM_PROMPT, prompt)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never block the pipeline
        logger.warning(f"Narrator LLM call failed, falling back to structured summary: {exc}")
        top = result.candidates[0].name if result.candidates else "none"
        return (
            f"(LLM summary unavailable) Top candidate: {top}. "
            f"{len(result.safety_flags)} safety flag(s) raised. "
            "Review structured candidates and flags directly."
        )
