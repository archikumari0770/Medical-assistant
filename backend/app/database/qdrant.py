"""
Qdrant connection layer -- hybrid (dense + sparse) retrieval.

Each point is stored with TWO named vectors:
  - "dense":  a semantic embedding (BAAI/bge-small-en-v1.5, 384-dim) --
    good at catching paraphrases and conceptual similarity.
  - "sparse": a BM25-style sparse embedding (Qdrant/bm25) -- good at
    catching exact term matches (drug names, specific clinical terms)
    that a dense embedding can blur together.

A query searches both and fuses the two ranked lists with Reciprocal
Rank Fusion (RRF) via Qdrant's Query API (query_points + prefetch).
This is the hybrid-search pattern Qdrant's own docs recommend -- pure
dense retrieval alone is no longer considered sufficient for anything
where exact terminology matters, which is most of clinical text.
"""
from __future__ import annotations

from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.config import settings

_client: AsyncQdrantClient | None = None

DENSE_DIM = 384  # matches BAAI/bge-small-en-v1.5


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


async def ensure_collections() -> None:
    """
    Creates the two collections with a dense+sparse named-vector schema
    if they don't already exist in that shape. If a collection exists
    from before this hybrid-search upgrade (single unnamed dense
    vector), it's dropped and recreated -- the two collections only
    ever hold re-derivable demo/indexed content, not irreplaceable
    data, so this avoids yet another manual migration step.
    """
    client = get_client()
    for name in (settings.qdrant_collection_patient, settings.qdrant_collection_medical):
        needs_create = True
        if await client.collection_exists(name):
            try:
                info = await client.get_collection(name)
                vectors_config = info.config.params.vectors
                is_hybrid_schema = isinstance(vectors_config, dict) and "dense" in vectors_config
            except Exception:
                # Can't confirm the schema — don't risk destroying real
                # indexed data over an introspection quirk; leave it be.
                is_hybrid_schema = True

            if is_hybrid_schema:
                needs_create = False
            else:
                await client.delete_collection(name)

        if needs_create:
            await client.create_collection(
                collection_name=name,
                vectors_config={
                    "dense": models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE),
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(),
                },
            )


async def upsert_hybrid(
    collection: str,
    ids: list[str],
    dense_vectors: list[list[float]],
    sparse_vectors: list[dict[str, list]],
    payloads: list[dict[str, Any]],
) -> None:
    """sparse_vectors: list of {"indices": [...], "values": [...]} dicts,
    one per point, as produced by FastEmbed's SparseTextEmbedding."""
    client = get_client()
    points = [
        models.PointStruct(
            id=ids[i],
            vector={
                "dense": dense_vectors[i],
                "sparse": models.SparseVector(
                    indices=sparse_vectors[i]["indices"],
                    values=sparse_vectors[i]["values"],
                ),
            },
            payload=payloads[i],
        )
        for i in range(len(ids))
    ]
    await client.upsert(collection_name=collection, points=points)


async def hybrid_search(
    collection: str,
    dense_query: list[float],
    sparse_query: dict[str, list],
    top_k: int = 5,
    prefetch_limit: int = 20,
    query_filter: models.Filter | None = None,
) -> list[dict[str, Any]]:
    """
    Runs dense and sparse search in parallel (each returning up to
    prefetch_limit candidates), then fuses the two ranked lists with
    Reciprocal Rank Fusion and returns the top_k fused results.
    """
    client = get_client()
    result = await client.query_points(
        collection_name=collection,
        prefetch=[
            models.Prefetch(
                query=dense_query,
                using="dense",
                limit=prefetch_limit,
                filter=query_filter,
            ),
            models.Prefetch(
                query=models.SparseVector(indices=sparse_query["indices"], values=sparse_query["values"]),
                using="sparse",
                limit=prefetch_limit,
                filter=query_filter,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )
    return [{"id": p.id, "score": p.score, **(p.payload or {})} for p in result.points]


async def count_points(collection: str, query_filter: models.Filter | None = None) -> int:
    client = get_client()
    result = await client.count(collection_name=collection, count_filter=query_filter)
    return result.count


async def fetch_by_title(collection: str, title_substring: str, limit: int = 200) -> list[dict[str, Any]]:
    """
    Exact, non-semantic lookup: returns every chunk whose payload title
    contains title_substring, in indexing order (not similarity-ranked).

    This is the core GraphRAG primitive: when the caller already knows,
    from graph structure, exactly which document it wants (e.g. "the
    reference document for the condition named 'Migraine'"), there's no
    reason to ask an embedding model to *guess* via similarity search —
    that guess can be wrong in ways an exact lookup can't be. In
    particular, embedding similarity struggles to distinguish "the
    document about X" from "the document about explicitly NOT having X"
    (see the negation-blindness finding in scripts/eval_rag.py); a
    graph-driven exact fetch sidesteps that failure mode entirely.

    Implementation note: this does a full collection scroll and filters
    client-side by substring match, which is simple and correct at this
    corpus's scale (dozens of documents). A collection with many more
    documents would instead want a Qdrant payload index on `title` with
    server-side full-text matching (models.MatchText) rather than
    scrolling everything.
    """
    client = get_client()
    all_points, _ = await client.scroll(collection_name=collection, limit=limit, with_payload=True)
    needle = title_substring.lower()
    return [
        {"id": p.id, **(p.payload or {})}
        for p in all_points
        if needle in (p.payload or {}).get("title", "").lower()
    ]