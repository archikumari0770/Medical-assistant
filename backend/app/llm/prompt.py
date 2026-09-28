"""
Prompt templates for the LLM narrator. Kept separate from client.py so
prompt iteration doesn't require touching API plumbing.
"""
from __future__ import annotations

from app.models.analysis import AnalysisResult

NARRATOR_SYSTEM_PROMPT = """\
You are a clinical decision-support assistant writing a summary for a \
licensed clinician who will review and validate every claim before acting \
on it. You are summarizing pre-computed evidence — a knowledge-graph-derived \
differential and retrieved literature/history snippets — not diagnosing on \
your own authority.

Rules:
- Never state a diagnosis as fact. Use hedged language ("consistent with", \
"may indicate", "consider").
- Always mention any critical safety flags first, prominently.
- Note when evidence is thin or conflicting rather than glossing over it.
- When evidence includes 'graph_differential' entries, use them to explicitly \
explain why the top candidate is favored over that specific alternative, \
citing the distinguishing feature given. When a 'graph_differential_reference' \
snippet is also present for that same alternative, use it to ground the \
contrast in what that alternative actually looks like, not just an assertion.
- Keep the summary concise: a short paragraph plus a brief bullet list of \
candidates in ranked order.
- End by reminding the reader this is decision support, not a diagnosis, \
and clinical judgment and further workup are required.
"""


def build_narrator_prompt(result: AnalysisResult) -> str:
    lines = [f"Patient ID: {result.patient_id}", ""]

    if result.safety_flags:
        lines.append("SAFETY FLAGS:")
        for flag in result.safety_flags:
            lines.append(f"- [{flag.severity.upper()}] {flag.message} (triggered by: {flag.triggered_by})")
        lines.append("")

    lines.append("CANDIDATE CONDITIONS (ranked):")
    for i, candidate in enumerate(result.candidates, start=1):
        lines.append(f"{i}. {candidate.name} (relative score: {candidate.score})")
        for evidence in candidate.supporting_evidence:
            lines.append(f"   + [{evidence.source}] {evidence.description}")
        for evidence in candidate.conflicting_evidence:
            lines.append(f"   - [conflict/{evidence.source}] {evidence.description}")
        if candidate.uncertainty_notes:
            lines.append(f"   ! {candidate.uncertainty_notes}")

    lines.append("")
    lines.append("Write the clinician-facing summary described in the system prompt.")
    return "\n".join(lines)