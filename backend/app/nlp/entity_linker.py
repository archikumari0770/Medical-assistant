"""
Links extracted symptom phrases to canonical Symptom nodes in the Neo4j
knowledge graph (see app/graph/schema.py), so downstream graph queries
can be run by node ID rather than fuzzy string matching every time.
"""
from __future__ import annotations

from app.database.neo4j import run_query


async def link_symptoms_to_graph(symptom_phrases: list[str]) -> dict[str, str | None]:
    """Returns {phrase: canonical_symptom_id or None if not found}."""
    if not symptom_phrases:
        return {}

    records = await run_query(
        """
        UNWIND $phrases AS phrase
        OPTIONAL MATCH (s:Symptom)
        WHERE toLower(s.name) = toLower(phrase) OR toLower(phrase) IN s.synonyms
        RETURN phrase, s.id AS symptom_id
        """,
        {"phrases": symptom_phrases},
    )
    return {r["phrase"]: r.get("symptom_id") for r in records}
