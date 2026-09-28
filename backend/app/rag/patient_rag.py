"""
Patient-scoped RAG: indexes a patient's own documents (visit notes,
discharge summaries, prior labs) and retrieves relevant chunks scoped
strictly to that one patient_id via a Qdrant payload filter.

Indexing pipeline per document: recursive chunking -> Contextual
Retrieval (LLM-generated per-chunk context) -> dense + sparse
embeddings of the contextualized text -> upsert as hybrid points.

Retrieval pipeline per query: dense + sparse embed the query -> hybrid
search with RRF fusion (wide net, cheap) -> cross-encoder rerank the
candidates (narrow, precise) -> return the top_k after reranking.
"""
from __future__ import annotations

import asyncio
import uuid

from qdrant_client import models

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

_RERANK_CANDIDATES = 15  # how many hybrid-search hits to pull before reranking


async def index_patient_document(patient_id: str, title: str, text: str) -> str:
    document_id = str(uuid.uuid4())
    chunks = chunk_text(text)
    if not chunks:
        return document_id

    # Contextual Retrieval: generate a situating blurb per chunk, in
    # parallel, before embedding. See app/rag/contextual.py.
    contexts = await asyncio.gather(*[generate_chunk_context(title, text, chunk) for chunk in chunks])
    embedding_texts = [build_embedding_text(ctx, chunk) for ctx, chunk in zip(contexts, chunks)]

    dense_vectors = embed_dense_batch(embedding_texts)
    sparse_vectors = embed_sparse_batch(embedding_texts)

    ids = [str(uuid.uuid4()) for _ in chunks]
    payloads = [
        {
            "patient_id": patient_id,
            "document_id": document_id,
            "title": title,
            "chunk_index": i,
            "text": chunk,  # original, uncontextualized — what gets shown/cited
            "context": ctx,
        }
        for i, (chunk, ctx) in enumerate(zip(chunks, contexts))
    ]

    await qdrant.upsert_hybrid(
        settings.qdrant_collection_patient,
        ids=ids,
        dense_vectors=dense_vectors,
        sparse_vectors=sparse_vectors,
        payloads=payloads,
    )
    return document_id


async def patient_has_indexed_documents(patient_id: str) -> bool:
    """Used by the admin delete-patient safety check — a patient with any
    indexed notes isn't 'empty' even if their Postgres tables are."""
    query_filter = models.Filter(
        must=[models.FieldCondition(key="patient_id", match=models.MatchValue(value=patient_id))]
    )
    count = await qdrant.count_points(settings.qdrant_collection_patient, query_filter=query_filter)
    return count > 0


async def search_patient_documents(patient_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Hybrid search restricted to a single patient's documents (the
    filter is what prevents cross-patient data leakage), followed by a
    cross-encoder rerank of the fused candidates."""
    query_filter = models.Filter(
        must=[models.FieldCondition(key="patient_id", match=models.MatchValue(value=patient_id))]
    )

    dense_query = embed_dense(query)
    sparse_query = embed_sparse(query)

    candidates = await qdrant.hybrid_search(
        settings.qdrant_collection_patient,
        dense_query=dense_query,
        sparse_query=sparse_query,
        top_k=_RERANK_CANDIDATES,
        query_filter=query_filter,
    )
    if not candidates:
        return []

    scores = rerank(query, [c.get("text", "") for c in candidates])
    for candidate, score in zip(candidates, scores):
        candidate["rerank_score"] = score

    candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    return candidates[:top_k]