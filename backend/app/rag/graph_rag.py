"""
GraphRAG: retrieval driven by graph structure, not just embedding
similarity.

The knowledge graph and the vector store were, until this module,
completely separate systems — a candidate condition was found via graph
edges, then a SEPARATE semantic search asked an embedding model to guess
which indexed document was "about" it. This module replaces that guess
with an exact fetch, and adds something pure vector RAG cannot produce
on its own: graph-guided contrastive retrieval.

Two things the graph gives us that embedding similarity cannot:

1. Exact entity identity. Once the graph tells us a candidate is
   "Migraine," we already know precisely which reference document
   corresponds to it — there's no ambiguity to resolve via similarity
   search, so we fetch it by exact title match instead (see
   app/database/qdrant.py's fetch_by_title).

2. Explicit contrastive relationships. The graph's DIFFERENTIAL_OF edges
   name exactly which other conditions are worth contrasting against,
   with a human-authored distinguishing_feature. This is precisely the
   kind of "not X, but Y" relationship that embedding similarity is
   demonstrably bad at (see the negation-blindness finding in
   scripts/eval_rag.py) — describing one condition by negating another's
   symptoms creates false similarity, not true contrast, when left to an
   embedding model. The graph sidesteps this entirely: it already knows
   the contrast, so no similarity judgment is needed at all.

Used by app/decision/candidate_generator.py to ground each candidate
with both its own reference material and its differential neighbors'
material, giving the LLM narrator what it needs to make an actual
differential argument rather than a single-condition summary.
"""
from __future__ import annotations

from app.config import settings
from app.database import qdrant


async def get_own_reference(condition_name: str, max_chunks: int = 2) -> list[dict]:
    """The candidate's own reference document, fetched by exact identity."""
    chunks = await qdrant.fetch_by_title(settings.qdrant_collection_medical, condition_name)
    return chunks[:max_chunks]


async def get_reference_snippet(condition_name: str) -> str | None:
    """A short snippet of another condition's own reference document —
    used to ground a differential contrast in that condition's own
    positively-framed description, rather than in a negation of it."""
    chunks = await qdrant.fetch_by_title(settings.qdrant_collection_medical, condition_name)
    return chunks[0]["text"] if chunks else None