"""
General medical-knowledge RAG: retrieves relevant guideline/literature
excerpts (not patient-specific) to ground candidate reasoning and the
final narrative summary. Same pipeline as patient_rag.py — see that
file's docstring for the retrieval architecture.

Populate this collection via scripts/seed_medical_knowledge.py, or by
calling index_medical_reference directly for your own material.
"""
from __future__ import annotations

import asyncio
import uuid

from app.config import settings
from app.database import qdrant
from app.rag.contextual import build_embedding_text, generate_chunk_context
from app.rag.retriever import (
    chunk_text,
    embed_dense,
    embed_dense_batch,
    embed_sparse,
    embed_sparse_batch,
    rerank,
)

_RERANK_CANDIDATES = 15


async def index_medical_reference(title: str, text: str, source: str = "internal-reference") -> str:
    """
    Chunks, contextualizes, embeds (dense + sparse), and indexes a piece
    of medical reference material into the shared medical_knowledge
    collection.

    IMPORTANT: only index material you have the right to store and reuse
    this way — original writing, licensed content, or your own
    institution's guidelines. Don't index copyrighted third-party
    literature verbatim without permission.
    """
    document_id = str(uuid.uuid4())
    chunks = chunk_text(text)
    if not chunks:
        return document_id

    contexts = await asyncio.gather(*[generate_chunk_context(title, text, chunk) for chunk in chunks])
    embedding_texts = [build_embedding_text(ctx, chunk) for ctx, chunk in zip(contexts, chunks)]

    dense_vectors = embed_dense_batch(embedding_texts)
    sparse_vectors = embed_sparse_batch(embedding_texts)

    ids = [str(uuid.uuid4()) for _ in chunks]
    payloads = [
        {
            "title": title,
            "document_id": document_id,
            "chunk_index": i,
            "text": chunk,
            "context": ctx,
            "source": source,
        }
        for i, (chunk, ctx) in enumerate(zip(chunks, contexts))
    ]

    await qdrant.upsert_hybrid(
        settings.qdrant_collection_medical,
        ids=ids,
        dense_vectors=dense_vectors,
        sparse_vectors=sparse_vectors,
        payloads=payloads,
    )
    return document_id


async def search_medical_literature(query: str, top_k: int = 5) -> list[dict]:
    dense_query = embed_dense(query)
    sparse_query = embed_sparse(query)

    candidates = await qdrant.hybrid_search(
        settings.qdrant_collection_medical,
        dense_query=dense_query,
        sparse_query=sparse_query,
        top_k=_RERANK_CANDIDATES,
    )
    if not candidates:
        return []

    scores = rerank(query, [c.get("text", "") for c in candidates])
    for candidate, score in zip(candidates, scores):
        candidate["rerank_score"] = score

    candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    return candidates[:top_k]


async def gather_context_for_condition(condition_name: str, top_k: int = 3) -> list[dict]:
    """
    Semantic search for literature about a condition, by similarity.

    NOTE: candidate grounding in the decision pipeline no longer calls
    this — see app/rag/graph_rag.py, which fetches a candidate's (and its
    differential neighbors') reference material by exact graph-known
    identity instead of asking an embedding model to guess via
    similarity. This function is kept as a general-purpose semantic
    search utility for open-ended queries where no graph anchor exists.
    """
    return await search_medical_literature(query=condition_name, top_k=top_k)