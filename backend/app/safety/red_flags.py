"""
Red-flag symptom checks — combinations or individual symptoms that
should trigger an urgent-care warning regardless of what the
differential-diagnosis ranking says.

This list is a starting point only and is NOT a substitute for clinical
triage protocols. Expand/validate with clinician input before any real
use, and always keep this check upstream/independent of the ranking
logic so a red flag can never be silently outranked.
"""
from __future__ import annotations

from app.models.analysis import SafetyFlag

# (trigger phrase, message) — case-insensitive substring match against symptoms.
CRITICAL_SINGLE_SYMPTOMS = {
    "chest pain": "Chest pain can indicate a cardiac emergency — recommend urgent evaluation.",
    "shortness of breath": "Shortness of breath may indicate a respiratory or cardiac emergency.",
    "confusion": "New confusion can indicate stroke, sepsis, or another acute process.",
}

CRITICAL_COMBINATIONS = [
    ({"fever", "confusion"}, "Fever with confusion may indicate sepsis or CNS infection — urgent evaluation recommended."),
    ({"chest pain", "shortness of breath"}, "Chest pain with shortness of breath is a classic combination for cardiac/pulmonary emergencies."),
]


async def check_red_flags(symptoms: list[str]) -> list[SafetyFlag]:
    flags: list[SafetyFlag] = []
    symptom_set = {s.lower() for s in symptoms}

    for symptom, message in CRITICAL_SINGLE_SYMPTOMS.items():
        if symptom in symptom_set:
            flags.append(SafetyFlag(severity="critical", message=message, triggered_by=symptom))

    for combo, message in CRITICAL_COMBINATIONS:
        if combo.issubset(symptom_set):
            flags.append(SafetyFlag(severity="critical", message=message, triggered_by=" + ".join(sorted(combo))))

    return flags
