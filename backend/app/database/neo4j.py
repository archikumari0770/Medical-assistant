"""
Neo4j connection layer.

Stores the medical knowledge graph: diseases, symptoms, medications,
lab findings and the relationships between them (CAUSES, TREATS,
CONTRAINDICATES, INTERACTS_WITH, etc). See app/graph/schema.py.
"""
from __future__ import annotations

from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import settings

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def run_query(
    query: str,
    parameters: dict[str, Any] | None = None,
    database: str = "neo4j",
) -> list[dict[str, Any]]:
    """Run a single Cypher query and return records as plain dicts."""
    driver = get_driver()
    async with driver.session(database=database) as session:
        result = await session.run(query, parameters or {})
        records = [record.data() async for record in result]
        return records


async def verify_connectivity() -> bool:
    try:
        driver = get_driver()
        await driver.verify_connectivity()
        return True
    except Exception:
        return False
