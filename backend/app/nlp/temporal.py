"""
Simple temporal expression extraction ("for 3 days", "since last week").

Used to attach duration/onset context to symptoms. Kept intentionally
lightweight — consider SUTime or an LLM call for richer normalization.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

DURATION_RE = re.compile(
    r"\b(?:for|since|over the (?:last|past))\s+"
    r"(\d+|a|an|one|two|three|four|five|six|seven|couple(?:\s+of)?)\s+"
    r"(day|days|week|weeks|month|months|hour|hours|year|years)\b",
    re.IGNORECASE,
)


@dataclass
class TemporalMention:
    raw_text: str
    quantity_text: str
    unit: str


def extract_temporal_context(text: str) -> list[TemporalMention]:
    mentions = []
    for match in DURATION_RE.finditer(text):
        mentions.append(
            TemporalMention(
                raw_text=match.group(0),
                quantity_text=match.group(1),
                unit=match.group(2).lower(),
            )
        )
    return mentions
