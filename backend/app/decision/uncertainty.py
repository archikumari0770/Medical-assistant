"""
Utilities for summarizing overall confidence/uncertainty across a set of
candidates — used to decide, e.g., whether the narrator should stress
that a workup is inconclusive and further evaluation is needed.
"""
from __future__ import annotations

from app.models.analysis import CandidateCondition


def overall_confidence_label(candidates: list[CandidateCondition]) -> str:
    """Returns a coarse label describing how separated/confident the
    candidate set is — never a precise probability."""
    if not candidates:
        return "no_candidates"

    top = candidates[0].score
    second = candidates[1].score if len(candidates) > 1 else 0.0

    if top < 0.3:
        return "low_confidence"
    if top - second < 0.15:
        return "ambiguous_differential"
    return "moderate_to_high_separation"
