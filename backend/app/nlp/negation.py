"""
Lightweight negation handling.

Removes clauses following common negation cues so the extractor doesn't
pick up "no fever", "denies chest pain", "ruled out pneumonia", etc. as
positive findings. This is a simple heuristic (similar in spirit to the
NegEx algorithm) — replace with a proper NegEx/ConText implementation
for anything beyond prototyping.
"""
from __future__ import annotations

import re

NEGATION_CUES = [
    "no ", "not ", "denies ", "denied ", "without ", "negative for ",
    "ruled out ", "rules out ", "absence of ", "free of ",
]

# Stop the negated clause at the next sentence boundary or conjunction.
CLAUSE_END = re.compile(r"[.;\n]|(?:\bbut\b)|(?:\bhowever\b)")


def strip_negated_phrases(text: str) -> str:
    lowered = text
    for cue in NEGATION_CUES:
        pattern = re.compile(re.escape(cue), re.IGNORECASE)
        while True:
            match = pattern.search(lowered)
            if not match:
                break
            end_match = CLAUSE_END.search(lowered, match.end())
            end = end_match.start() if end_match else len(lowered)
            # Remove the negated clause entirely (cue + following text up to boundary)
            lowered = lowered[: match.start()] + lowered[end:]
    return lowered
