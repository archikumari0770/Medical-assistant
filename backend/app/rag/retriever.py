"""
Shared retrieval primitives: embeddings, reranking, and chunking, used
by both patient_rag.py and medical_rag.py.

Stack, and why:

  - Dense embeddings: BAAI/bge-small-en-v1.5 via FastEmbed. BGE models
    are a current, strong open embedding family (meaningfully ahead of
    older general-purpose SBERT models like MiniLM on retrieval
    benchmarks) and FastEmbed runs them on ONNX Runtime rather than
    PyTorch -- no torch/transformers/tensorflow dependency chain to
    fight with, and fast on CPU.

  - Sparse embeddings: Qdrant/bm25 via FastEmbed -- a BM25-style sparse
    vector. Dense embeddings are good at "this means the same thing";
    sparse is good at "this contains the same exact term" (drug names,
    ICD codes, specific clinical phrases). Combining both and fusing
    with RRF (see app/database/qdrant.py) is the standard modern
    hybrid-search pattern -- dense-only retrieval is no longer
    considered sufficient on its own for text where exact terminology
    carries real meaning.

  - Reranking: a cross-encoder (via FastEmbed's TextCrossEncoder) reads
    the query and each candidate chunk TOGETHER and scores relevance
    directly, which is far more accurate than comparing two
    independently-computed embeddings -- but too slow to run over an
    entire collection. So retrieval is two-stage: hybrid search casts
    a wide net (cheap, approximate), then the reranker re-scores just
    those candidates (expensive, precise) before the top few go to the
    LLM. This bi-encoder-then-cross-encoder pattern is standard in any
    production RAG pipeline built after ~2023.
"""
from __future__ import annotations

import re
from functools import lru_cache

from fastembed import SparseTextEmbedding, TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder

_DENSE_MODEL = "BAAI/bge-small-en-v1.5"
_SPARSE_MODEL = "Qdrant/bm25"
_RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


@lru_cache
def _dense_model() -> TextEmbedding:
    return TextEmbedding(model_name=_DENSE_MODEL)


@lru_cache
def _sparse_model() -> SparseTextEmbedding:
    return SparseTextEmbedding(model_name=_SPARSE_MODEL)


@lru_cache
def _reranker_model() -> TextCrossEncoder:
    return TextCrossEncoder(model_name=_RERANKER_MODEL)


def embed_dense(text: str) -> list[float]:
    return list(_dense_model().embed([text]))[0].tolist()


def embed_dense_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return [v.tolist() for v in _dense_model().embed(texts)]


def embed_sparse(text: str) -> dict[str, list]:
    result = list(_sparse_model().embed([text]))[0]
    return {"indices": result.indices.tolist(), "values": result.values.tolist()}


def embed_sparse_batch(texts: list[str]) -> list[dict[str, list]]:
    if not texts:
        return []
    return [{"indices": r.indices.tolist(), "values": r.values.tolist()} for r in _sparse_model().embed(texts)]


def rerank(query: str, documents: list[str]) -> list[float]:
    """Returns a relevance score per document, same order as input."""
    if not documents:
        return []
    return list(_reranker_model().rerank(query, documents))


# ---------------------------------------------------------------------
# Chunking: recursive splitting rather than a blind fixed-width window.
# Tries to break on paragraph boundaries first, falling back to
# sentence boundaries, and only falls back to a hard character cut if a
# single sentence is still too long. This avoids severing a sentence
# (and therefore its meaning) mid-word, which a naive character-window
# splitter does regularly.
# ---------------------------------------------------------------------
def chunk_text(text: str, max_chars: int = 500, overlap: int = 60) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buffer = ""

    def flush():
        nonlocal buffer
        if buffer.strip():
            chunks.append(buffer.strip())
        buffer = ""

    for para in paragraphs:
        candidate = f"{buffer}\n\n{para}".strip() if buffer else para
        if len(candidate) <= max_chars:
            buffer = candidate
            continue

        flush()
        if len(para) <= max_chars:
            buffer = para
            continue

        # Paragraph itself is too long — split on sentence boundaries.
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for sentence in sentences:
            candidate = f"{buffer} {sentence}".strip() if buffer else sentence
            if len(candidate) <= max_chars:
                buffer = candidate
                continue
            flush()
            if len(sentence) <= max_chars:
                buffer = sentence
            else:
                # Even a single sentence is too long — hard character
                # windows as a last resort, with overlap.
                start = 0
                while start < len(sentence):
                    end = min(start + max_chars, len(sentence))
                    chunks.append(sentence[start:end])
                    if end == len(sentence):
                        break
                    start = end - overlap
    flush()

    # Light overlap between adjacent chunks so a fact split across a
    # boundary is still likely to appear whole in at least one chunk.
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for prev, cur in zip(chunks, chunks[1:]):
            tail = prev[-overlap:] if len(prev) > overlap else prev
            overlapped.append(f"{tail} {cur}".strip())
        return overlapped

    return chunks