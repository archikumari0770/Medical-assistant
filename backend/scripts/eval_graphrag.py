"""
Evaluates the GraphRAG differential-grounding contribution specifically --
NOT retrieval quality (that's scripts/eval_rag.py). This tests a
different, more specific claim: when two clinically confusable
conditions both appear as candidates for a shared symptom, does the real
pipeline (app.decision.candidate_generator.generate_candidates) actually
surface correct, bidirectional differential evidence between them?

This matters because GraphRAG was added to fix a specific, previously
measured failure (negation-blindness in embedding-based retrieval -- see
scripts/eval_rag.py's history). Building the mechanism isn't the same as
confirming it does what it was built for; this script closes that gap.

Each test case is a symptom set chosen so that BOTH conditions in a known
DIFFERENTIAL_OF pair (see scripts/seed_neo4j.py's DIFFERENTIALS) appear
as graph candidates. For each, we check:

  1. both_present         - did both conditions appear as candidates at all?
  2. a_differentiates_b    - does condition A's evidence explicitly name
                             and distinguish it from condition B?
  3. b_differentiates_a    - the same, in the other direction
  4. has_reference_snippet - is the contrast grounded in the neighbor's
                             own reference text, not just an assertion?

This calls the real pipeline function against your actual running Neo4j
and Qdrant -- no mocking -- so it also serves as an integration check.

Run from backend/ (after seed_neo4j.py and seed_medical_knowledge.py):
    python -m scripts.eval_graphrag
"""
import asyncio

from app.database.neo4j import close_driver
from app.decision.candidate_generator import generate_candidates

# (shared_symptoms, condition_a, condition_b) -- symptoms chosen so both
# conditions co-occur as graph candidates, and a DIFFERENTIAL_OF edge
# exists between them in scripts/seed_neo4j.py's DIFFERENTIALS.
TEST_PAIRS = [
    (["headache"], "Migraine", "Tension-Type Headache"),
    (["headache"], "Migraine", "Cluster Headache"),
    (["productive cough"], "Community-Acquired Pneumonia", "Acute Bronchitis"),
    (["chest pain"], "Acute Coronary Syndrome", "Costochondritis"),
    (["abdominal pain", "nausea"], "Appendicitis", "Gastroenteritis"),
    (["abdominal pain", "nausea"], "Cholecystitis", "Peptic Ulcer Disease"),
    (["shortness of breath"], "Heart Failure Exacerbation", "Community-Acquired Pneumonia"),
    (["shortness of breath"], "Anaphylaxis", "Asthma Exacerbation"),
    (["nausea", "vomiting"], "Diabetic Ketoacidosis", "Gastroenteritis"),
    (["dizziness", "anxiety"], "Hypoglycemia", "Panic Attack"),
    (["cough", "sore throat"], "Influenza", "Common Cold"),
    (["fever", "cough"], "Influenza", "COVID-19"),
]


def find_candidate(candidates, name: str):
    return next((c for c in candidates if c.name == name), None)


def differentiates(candidate, other_name: str) -> bool:
    if not candidate:
        return False
    return any(
        e.source == "graph_differential" and other_name.lower() in e.description.lower()
        for e in candidate.supporting_evidence
    )


def has_reference_snippet(candidate, other_name: str) -> bool:
    if not candidate:
        return False
    return any(
        e.source == "graph_differential_reference" and other_name.lower() in e.description.lower()
        for e in candidate.supporting_evidence
    )


async def run():
    print(f"Running {len(TEST_PAIRS)} confusable-pair test cases against the real pipeline...\n")

    results = []
    for symptoms, cond_a, cond_b in TEST_PAIRS:
        candidates = await generate_candidates("eval-patient", symptoms)
        candidate_a = find_candidate(candidates, cond_a)
        candidate_b = find_candidate(candidates, cond_b)

        both_present = candidate_a is not None and candidate_b is not None
        a_diff_b = differentiates(candidate_a, cond_b)
        b_diff_a = differentiates(candidate_b, cond_a)
        a_ref = has_reference_snippet(candidate_a, cond_b)
        b_ref = has_reference_snippet(candidate_b, cond_a)

        passed = both_present and a_diff_b and b_diff_a
        results.append(
            {
                "symptoms": symptoms,
                "pair": (cond_a, cond_b),
                "both_present": both_present,
                "a_diff_b": a_diff_b,
                "b_diff_a": b_diff_a,
                "a_ref": a_ref,
                "b_ref": b_ref,
                "passed": passed,
            }
        )

    print(f"{'Pass':<6}{'Symptoms':<30}{'Pair':<50}{'Both':<6}{'A->B':<6}{'B->A':<6}{'Refs':<6}")
    print("-" * 110)
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        symptoms_str = ", ".join(r["symptoms"])
        pair_str = f"{r['pair'][0]} / {r['pair'][1]}"
        refs = "yes" if (r["a_ref"] and r["b_ref"]) else ("some" if (r["a_ref"] or r["b_ref"]) else "no")
        print(
            f"{mark:<6}{symptoms_str:<30}{pair_str:<50}"
            f"{'y' if r['both_present'] else 'n':<6}{'y' if r['a_diff_b'] else 'n':<6}"
            f"{'y' if r['b_diff_a'] else 'n':<6}{refs:<6}"
        )

    n = len(results)
    passed = sum(1 for r in results if r["passed"])
    print(f"\n{passed}/{n} pairs correctly surfaced bidirectional differential evidence ({passed / n:.0%})")

    failures = [r for r in results if not r["passed"]]
    if failures:
        print("\nFailures -- diagnose before trusting the differential grounding claim:")
        for r in failures:
            reason = []
            if not r["both_present"]:
                reason.append("one or both conditions didn't appear as candidates for this symptom set")
            if r["both_present"] and not r["a_diff_b"]:
                reason.append(f"{r['pair'][0]}'s evidence didn't name/distinguish {r['pair'][1]}")
            if r["both_present"] and not r["b_diff_a"]:
                reason.append(f"{r['pair'][1]}'s evidence didn't name/distinguish {r['pair'][0]}")
            print(f"  {r['pair'][0]} / {r['pair'][1]}: {'; '.join(reason)}")

    await close_driver()


if __name__ == "__main__":
    asyncio.run(run())