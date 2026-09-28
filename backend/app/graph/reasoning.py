"""
Higher-level reasoning built on top of raw graph queries — e.g. building
a differential diagnosis set with distinguishing features, rather than
just a flat ranked list of conditions.
"""
from __future__ import annotations

from app.graph.queries import conditions_for_symptoms, differentials_for_condition


async def build_differential_set(symptoms: list[str], limit: int = 8) -> list[dict]:
    """
    Returns candidate conditions along with the distinguishing features
    that separate each one from its closest differentials — useful for
    the "why this and not that" explanation shown in the WhyPanel UI.
    """
    candidates = await conditions_for_symptoms(symptoms, limit=limit)

    enriched = []
    for cand in candidates:
        differentials = await differentials_for_condition(cand["condition_id"])
        enriched.append({**cand, "differentials": differentials})

    return enriched
