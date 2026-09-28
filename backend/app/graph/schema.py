"""
Knowledge graph schema for the medical KG stored in Neo4j.

Node labels:
  - Condition(id, name, icd10, description)
  - Symptom(id, name, synonyms: [string])
  - Medication(id, name, drug_class)
  - LabFinding(id, name, normal_range)

Relationships:
  - (Symptom)-[:INDICATES {weight: float}]->(Condition)
  - (Condition)-[:TREATED_BY]->(Medication)
  - (Medication)-[:INTERACTS_WITH {severity: string}]->(Medication)
  - (Medication)-[:CONTRAINDICATED_FOR]->(Condition)
  - (Condition)-[:ASSOCIATED_WITH]->(LabFinding)
  - (Condition)-[:DIFFERENTIAL_OF {distinguishing_feature: string}]->(Condition)

Run `apply_constraints()` once against a fresh database (also called
from scripts/seed_neo4j.py) to create uniqueness constraints/indexes.
"""
from __future__ import annotations

from app.database.neo4j import run_query

CONSTRAINTS = [
    "CREATE CONSTRAINT condition_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT medication_id IF NOT EXISTS FOR (m:Medication) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT labfinding_id IF NOT EXISTS FOR (l:LabFinding) REQUIRE l.id IS UNIQUE",
    "CREATE INDEX symptom_name IF NOT EXISTS FOR (s:Symptom) ON (s.name)",
    "CREATE INDEX condition_name IF NOT EXISTS FOR (c:Condition) ON (c.name)",
]


async def apply_constraints() -> None:
    for stmt in CONSTRAINTS:
        await run_query(stmt)
