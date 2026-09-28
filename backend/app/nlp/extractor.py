"""
Symptom/entity extraction from free-text clinical notes.

This starter version uses a simple keyword/phrase matcher against a
curated symptom vocabulary. Swap in a proper clinical NLP model
(e.g. a fine-tuned NER model, scispaCy, or an LLM extraction call)
for production use — this is intentionally simple so the pipeline
runs end-to-end out of the box.
"""
from __future__ import annotations

import re

from app.nlp.negation import strip_negated_phrases
from app.nlp.temporal import extract_temporal_context

# Mirrors the symptom set seeded into Neo4j by scripts/seed_neo4j.py —
# keep these in sync, or extracted symptoms won't link to graph nodes.
SYMPTOM_VOCAB = [
    "fever", "chills", "cough", "productive cough", "sore throat", "runny nose",
    "nasal congestion", "sneezing", "loss of taste or smell", "shortness of breath",
    "wheezing", "chest pain", "pleuritic chest pain", "palpitations", "leg swelling",
    "headache", "one-sided headache", "sensitivity to light", "visual aura",
    "facial swelling", "throat tightness", "hives", "nausea", "vomiting", "diarrhea",
    "abdominal pain", "right upper quadrant pain", "right lower quadrant pain",
    "heartburn", "black stools", "bloating", "fatigue", "muscle aches", "night sweats",
    "weight loss", "joint pain", "back pain", "dizziness", "confusion", "rash",
    "swelling", "urinary frequency", "painful urination", "flank pain",
    "excessive thirst", "fruity breath odor", "sweating", "tremor", "anxiety",
]


async def extract_symptoms(text: str) -> list[str]:
    """Return a de-duplicated list of symptom phrases found in free text,
    excluding phrases that are explicitly negated ("no fever", "denies cough")."""
    cleaned = strip_negated_phrases(text)
    lowered = cleaned.lower()

    found = set()
    for phrase in SYMPTOM_VOCAB:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            found.add(phrase)

    # Temporal context (e.g. "for 3 days") is extracted separately and can be
    # attached to encounters/candidates rather than folded into the symptom list.
    _ = extract_temporal_context(text)

    return sorted(found)