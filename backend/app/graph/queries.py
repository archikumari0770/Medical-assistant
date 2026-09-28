"""
Reusable Cypher queries against the medical knowledge graph.
"""
from __future__ import annotations

from app.database.neo4j import run_query


async def conditions_for_symptoms(symptom_names: list[str], limit: int = 15) -> list[dict]:
    """Find candidate conditions indicated by any of the given symptoms,
    ranked by the number of matching symptoms and cumulative edge weight."""
    if not symptom_names:
        return []
    return await run_query(
        """
        MATCH (s:Symptom)-[r:INDICATES]->(c:Condition)
        WHERE toLower(s.name) IN [x IN $symptoms | toLower(x)]
        WITH c, collect(DISTINCT s.name) AS matched_symptoms, sum(r.weight) AS total_weight
        RETURN c.id AS condition_id, c.name AS condition_name, c.description AS description,
               matched_symptoms, total_weight
        ORDER BY size(matched_symptoms) DESC, total_weight DESC
        LIMIT $limit
        """,
        {"symptoms": symptom_names, "limit": limit},
    )


async def medications_for_condition(condition_id: str) -> list[dict]:
    return await run_query(
        """
        MATCH (c:Condition {id: $condition_id})-[:TREATED_BY]->(m:Medication)
        RETURN m.id AS medication_id, m.name AS name, m.drug_class AS drug_class
        """,
        {"condition_id": condition_id},
    )


async def contraindications_for_medications(medication_names: list[str]) -> list[dict]:
    if not medication_names:
        return []
    return await run_query(
        """
        MATCH (m:Medication)-[:CONTRAINDICATED_FOR]->(c:Condition)
        WHERE toLower(m.name) IN [x IN $meds | toLower(x)]
        RETURN m.name AS medication, c.id AS condition_id, c.name AS condition_name
        """,
        {"meds": medication_names},
    )


async def interactions_between(medication_names: list[str]) -> list[dict]:
    if len(medication_names) < 2:
        return []
    return await run_query(
        """
        MATCH (m1:Medication)-[r:INTERACTS_WITH]-(m2:Medication)
        WHERE toLower(m1.name) IN [x IN $meds | toLower(x)]
          AND toLower(m2.name) IN [x IN $meds | toLower(x)]
          AND m1.id < m2.id
        RETURN m1.name AS medication_a, m2.name AS medication_b, r.severity AS severity
        """,
        {"meds": medication_names},
    )


async def differentials_for_condition(condition_id: str) -> list[dict]:
    return await run_query(
        """
        MATCH (c:Condition {id: $condition_id})-[r:DIFFERENTIAL_OF]-(other:Condition)
        RETURN other.id AS condition_id, other.name AS name, r.distinguishing_feature AS distinguishing_feature
        """,
        {"condition_id": condition_id},
    )
