"""
Generates an initial list of candidate conditions from the knowledge
graph (Symptom -> Condition edges), then grounds each one using GraphRAG:
its own reference material and its differential neighbors' material are
fetched by exact identity (see app/rag/graph_rag.py), not by asking an
embedding model to guess via semantic similarity.

Scoring/conflict-annotation happen in separate modules (scorer.py,
conflicts.py) so each stage stays testable in isolation.
"""
from __future__ import annotations

from app.graph.reasoning import build_differential_set
from app.models.analysis import CandidateCondition, EvidenceItem
from app.rag.graph_rag import get_own_reference, get_reference_snippet


async def generate_candidates(patient_id: str, symptoms: list[str]) -> list[CandidateCondition]:
    graph_candidates = await build_differential_set(symptoms)

    candidates: list[CandidateCondition] = []
    for gc in graph_candidates:
        evidence = [
            EvidenceItem(
                source="knowledge_graph",
                description=f"Matches symptoms: {', '.join(gc['matched_symptoms'])}",
                reference_id=gc["condition_id"],
            )
        ]

        # GraphRAG: fetch this candidate's own reference material by exact
        # identity, since the graph already told us precisely which
        # condition this is — no similarity guess needed.
        own_chunks = await get_own_reference(gc["condition_name"])
        for chunk in own_chunks:
            evidence.append(
                EvidenceItem(
                    source="medical_literature",
                    description=chunk.get("text", "")[:280],
                    reference_id=str(chunk.get("id")),
                )
            )

        # GraphRAG: for each graph-known differential neighbor, add both
        # the structured distinguishing feature (from the graph) and a
        # snippet of that neighbor's OWN reference material (fetched by
        # exact identity) — giving the LLM narrator a real contrastive
        # basis instead of a single-condition summary.
        for diff in gc.get("differentials", []):
            evidence.append(
                EvidenceItem(
                    source="graph_differential",
                    description=f"Differentiate from {diff['name']}: {diff['distinguishing_feature']}",
                    reference_id=diff["condition_id"],
                )
            )
            snippet = await get_reference_snippet(diff["name"])
            if snippet:
                evidence.append(
                    EvidenceItem(
                        source="graph_differential_reference",
                        description=f"{diff['name']}: {snippet[:200]}",
                        reference_id=diff["condition_id"],
                    )
                )

        candidates.append(
            CandidateCondition(
                name=gc["condition_name"],
                score=0.0,  # filled in by scorer.py
                supporting_evidence=evidence,
            )
        )

    return candidates