"""
Contextual Retrieval (Anthropic, published Sept 2024).

The problem it solves: a chunk taken out of its document often loses
the context that made it findable. A chunk that just says "the drug is
contraindicated in this population" is nearly useless for retrieval —
which drug? which population? which document? Embedding that chunk in
isolation buries the very thing a query would search for.

The fix: before embedding a chunk, ask the LLM to write a short (1-2
sentence) blurb situating that chunk within the whole document, then
embed CHUNK_CONTEXT + chunk together. The original, uncontextualized
chunk text is still what's stored/shown/cited — only the embedding
input changes. Anthropic's published internal benchmarks showed this
meaningfully reduces retrieval failure rate versus embedding raw
chunks. This is exactly that technique, using the same Claude client
already wired up for the narrator (see app/llm/client.py).
"""
from __future__ import annotations

from loguru import logger

from app.llm.client import complete

_SYSTEM_PROMPT = """\
You write short, factual context blurbs that help a search system find \
the right chunk of a document. Given a full document and one chunk from \
it, write 1-2 sentences that situate the chunk within the document -- \
what the document is about, and what specific subject the chunk covers. \
Be concrete: name the specific condition, medication, or topic. Do not \
restate the chunk's content in full, just enough context to make the \
chunk findable on its own. Respond with only the context blurb, nothing \
else -- no preamble, no quotation marks.
"""


async def generate_chunk_context(document_title: str, full_document: str, chunk: str) -> str:
    """
    Returns a short context blurb for the chunk, or "" if generation
    fails for any reason — indexing should never hard-fail just because
    this enrichment step couldn't run; it degrades to plain chunking.
    """
    prompt = (
        f"Document title: {document_title}\n\n"
        f"Full document:\n{full_document}\n\n"
        f"Chunk to contextualize:\n{chunk}"
    )
    try:
        context = await complete(_SYSTEM_PROMPT, prompt, max_tokens=120)
        return context.strip()
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never block indexing
        logger.warning(f"Contextual retrieval generation failed, indexing chunk without context: {exc}")
        return ""


def build_embedding_text(context: str, chunk: str) -> str:
    """What actually gets embedded — the original chunk is unchanged
    for display/citation purposes; only this derived text differs."""
    if not context:
        return chunk
    return f"{context}\n\n{chunk}"