"""
Thin async wrapper around the Anthropic API, used by narrator.py to
produce the final human-readable summary of an analysis run.
"""
from __future__ import annotations

from anthropic import AsyncAnthropic

from app.config import settings

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def complete(system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
    client = get_client()
    response = await client.messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
