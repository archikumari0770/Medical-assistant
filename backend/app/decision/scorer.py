"""
Scores candidate conditions on a relative 0-1 scale.

IMPORTANT: this is a heuristic relevance score for ranking candidates,
NOT a calibrated clinical probability. Never present `score` to a user
as "% chance of diagnosis" — see AnalysisResult.disclaimer.
"""
from __future__ import annotations

from app.models.analysis import CandidateCondition


def _evidence_weight(candidate: CandidateCondition) -> float:
    graph_hits = sum(1 for e in candidate.supporting_evidence if e.source == "knowledge_graph")
    literature_hits = sum(1 for e in candidate.supporting_evidence if e.source == "medical_literature")
    # Graph matches (direct symptom links) weighted more heavily than
    # loosely-related literature excerpts.
    return graph_hits * 1.0 + literature_hits * 0.3


async def score_candidates(candidates: list[CandidateCondition], patient_id: str) -> list[CandidateCondition]:
    if not candidates:
        return candidates

    raw_scores = [_evidence_weight(c) for c in candidates]
    max_score = max(raw_scores) or 1.0

    for candidate, raw in zip(candidates, raw_scores):
        candidate.score = round(raw / max_score, 3)

    return sorted(candidates, key=lambda c: c.score, reverse=True)
