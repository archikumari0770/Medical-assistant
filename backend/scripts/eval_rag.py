"""
Ablation study for the RAG retrieval pipeline, on a 55-query labeled test
set spanning all 26 conditions in medical_knowledge.

Compares FOUR configurations to isolate which component contributes what:
  1. dense-only        -- a single bi-encoder embedding, cosine similarity
  2. sparse-only        -- BM25-style term matching only
  3. hybrid              -- dense + sparse fused with Reciprocal Rank Fusion
  4. hybrid + rerank    -- (3) followed by cross-encoder reranking

Queries are tagged by category so results can be broken down, not just
aggregated -- an aggregate-only report can hide the fact that a method
excels at one failure mode and does nothing for another:
  - paraphrase   : natural language, no shared vocabulary with the source
                   document -- tests the dense side
  - exact_term   : built around one specific drug name / clinical term --
                   tests the sparse side
  - confusable   : deliberately close to a clinically similar condition --
                   tests reranking, and is the category where an earlier,
                   smaller version of this eval caught a real
                   negation-blindness failure in the embeddings

Metrics: Recall@3 and MRR (Mean Reciprocal Rank), computed overall and
per category.

Run from backend/ (after seed_medical_knowledge.py has populated the
collection):
    python -m scripts.eval_rag
"""
import asyncio
from collections import defaultdict

from app.config import settings
from app.database import qdrant
from app.rag.retriever import embed_dense, embed_sparse, rerank

# (query, expected_condition_name, category)
TEST_QUERIES = [
    ("sudden high fever with body aches and chills that hit within hours", "Influenza", "paraphrase"),
    ("oseltamivir treatment window", "Influenza", "exact_term"),
    ("stuffy nose and sneezing that built up gradually over a couple days, no real fever", "Common Cold", "paraphrase"),
    ("mild cold symptoms that came on slowly over a day or two", "Common Cold", "confusable"),
    ("lost my sense of smell along with a cough and tiredness", "COVID-19", "paraphrase"),
    ("SARS-CoV-2 infection symptoms", "COVID-19", "exact_term"),
    ("cough with fever that showed a spot on the chest x-ray", "Community-Acquired Pneumonia", "paraphrase"),
    ("azithromycin for lung infection", "Community-Acquired Pneumonia", "exact_term"),
    ("cough for two weeks after a cold, no fever, normal chest x-ray", "Acute Bronchitis", "paraphrase"),
    ("lingering productive cough after a respiratory infection with clear chest imaging", "Acute Bronchitis", "confusable"),
    ("wheezing and tightness in my chest that's worse at night", "Asthma Exacerbation", "paraphrase"),
    ("albuterol inhaler for breathing difficulty", "Asthma Exacerbation", "exact_term"),
    ("chest pressure with sweating and pain going into my arm", "Acute Coronary Syndrome", "paraphrase"),
    ("elevated troponin level", "Acute Coronary Syndrome", "exact_term"),
    ("contraindication for sumatriptan", "Acute Coronary Syndrome", "confusable"),
    ("chest tightness every time I climb stairs that goes away with rest", "Stable Angina", "paraphrase"),
    ("predictable exertional chest discomfort relieved by nitroglycerin", "Stable Angina", "confusable"),
    ("sharp chest pain that gets better when I lean forward", "Pericarditis", "paraphrase"),
    ("chest pain worse lying flat, better sitting up, with low fever", "Pericarditis", "confusable"),
    ("heart feels like it's fluttering and beating irregularly", "Atrial Fibrillation", "paraphrase"),
    ("anticoagulation with warfarin for irregular heart rhythm", "Atrial Fibrillation", "exact_term"),
    ("legs swollen and short of breath lying down at night", "Heart Failure Exacerbation", "paraphrase"),
    ("furosemide for fluid overload", "Heart Failure Exacerbation", "exact_term"),
    ("crampy stomach pain all over with lots of watery diarrhea", "Gastroenteritis", "paraphrase"),
    ("stomach bug going around with throwing up and loose stools", "Gastroenteritis", "paraphrase"),
    ("burning feeling rising up from my stomach after eating, worse lying down", "GERD", "paraphrase"),
    ("omeprazole for acid reflux", "GERD", "exact_term"),
    ("gnawing stomach pain that gets better for a bit after I eat", "Peptic Ulcer Disease", "paraphrase"),
    ("dark tarry stools with stomach pain", "Peptic Ulcer Disease", "confusable"),
    ("belly pain that started around my belly button and moved to the lower right side", "Appendicitis", "paraphrase"),
    ("abdominal pain that localized to one spot over several hours", "Appendicitis", "confusable"),
    ("sharp pain under my right ribs after eating a fatty meal", "Cholecystitis", "paraphrase"),
    ("right upper quadrant pain radiating to the shoulder blade", "Cholecystitis", "confusable"),
    ("headache that gets worse when I move around, with nausea and light bothering me", "Migraine", "paraphrase"),
    ("why does my head only hurt on one side and light makes it worse", "Migraine", "paraphrase"),
    ("headache on both sides, feels like pressure, no nausea", "Tension-Type Headache", "paraphrase"),
    ("band-like head pressure that isn't worse with activity", "Tension-Type Headache", "confusable"),
    ("severe headache around one eye that comes back daily for weeks then goes away for months", "Cluster Headache", "paraphrase"),
    ("one-sided eye pain with tearing and a stuffy nose on the same side", "Cluster Headache", "confusable"),
    ("burning when I pee and going to the bathroom constantly", "Urinary Tract Infection", "paraphrase"),
    ("ceftriaxone for bladder infection", "Urinary Tract Infection", "exact_term"),
    ("red warm swollen patch of skin that's spreading", "Cellulitis", "paraphrase"),
    ("skin infection after a cut that's tender and spreading", "Cellulitis", "confusable"),
    ("hives and my throat feels like it's closing up after eating peanuts", "Anaphylaxis", "paraphrase"),
    ("epinephrine for severe allergic reaction", "Anaphylaxis", "exact_term"),
    ("sudden intense fear with a racing heart and feeling like I'm going to die", "Panic Attack", "paraphrase"),
    ("chest symptoms and racing heart triggered by stress, resolves in half an hour", "Panic Attack", "confusable"),
    ("chest pain that gets worse when I press on it", "Costochondritis", "paraphrase"),
    ("reproducible chest wall tenderness with pain on deep breathing", "Costochondritis", "confusable"),
    ("extremely thirsty, peeing constantly, and my breath smells fruity", "Diabetic Ketoacidosis", "paraphrase"),
    ("elevated blood glucose and ketones", "Diabetic Ketoacidosis", "exact_term"),
    ("shaky, sweaty and confused after taking my insulin without eating", "Hypoglycemia", "paraphrase"),
    ("symptoms went away quickly after eating something sugary", "Hypoglycemia", "confusable"),
]


async def dense_only_search(query: str, top_k: int) -> list[dict]:
    client = qdrant.get_client()
    dense_query = embed_dense(query)
    result = await client.query_points(
        collection_name=settings.qdrant_collection_medical,
        query=dense_query,
        using="dense",
        limit=top_k,
        with_payload=True,
    )
    return [{"id": p.id, "score": p.score, **(p.payload or {})} for p in result.points]


async def sparse_only_search(query: str, top_k: int) -> list[dict]:
    client = qdrant.get_client()
    sparse_query = embed_sparse(query)
    result = await client.query_points(
        collection_name=settings.qdrant_collection_medical,
        query=qdrant.models.SparseVector(indices=sparse_query["indices"], values=sparse_query["values"]),
        using="sparse",
        limit=top_k,
        with_payload=True,
    )
    return [{"id": p.id, "score": p.score, **(p.payload or {})} for p in result.points]


async def hybrid_no_rerank_search(query: str, top_k: int) -> list[dict]:
    dense_query = embed_dense(query)
    sparse_query = embed_sparse(query)
    return await qdrant.hybrid_search(
        settings.qdrant_collection_medical,
        dense_query=dense_query,
        sparse_query=sparse_query,
        top_k=top_k,
    )


async def hybrid_rerank_search(query: str, top_k: int) -> list[dict]:
    dense_query = embed_dense(query)
    sparse_query = embed_sparse(query)
    candidates = await qdrant.hybrid_search(
        settings.qdrant_collection_medical,
        dense_query=dense_query,
        sparse_query=sparse_query,
        top_k=15,
    )
    if not candidates:
        return []
    scores = rerank(query, [c.get("text", "") for c in candidates])
    for c, s in zip(candidates, scores):
        c["rerank_score"] = s
    candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    return candidates[:top_k]


CONFIGURATIONS = {
    "dense-only": dense_only_search,
    "sparse-only": sparse_only_search,
    "hybrid": hybrid_no_rerank_search,
    "hybrid+rerank": hybrid_rerank_search,
}


def compute_metrics(labeled_results: list[tuple[str, str, list[dict]]], k: int) -> dict:
    """labeled_results: list of (expected_condition, category, results)."""
    hits = 0
    reciprocal_ranks = []
    per_category = defaultdict(lambda: {"hits": 0, "rr": [], "n": 0})

    for expected, category, results in labeled_results:
        rank = None
        for i, r in enumerate(results[:k], start=1):
            if expected.lower() in r.get("title", "").lower():
                rank = i
                break
        rr = 1 / rank if rank else 0.0
        if rank:
            hits += 1
        reciprocal_ranks.append(rr)

        per_category[category]["n"] += 1
        per_category[category]["rr"].append(rr)
        if rank:
            per_category[category]["hits"] += 1

    n = len(labeled_results)
    result = {
        f"recall@{k}": hits / n if n else 0.0,
        "mrr": sum(reciprocal_ranks) / n if n else 0.0,
    }
    for cat, data in per_category.items():
        result[f"mrr_{cat}"] = sum(data["rr"]) / data["n"] if data["n"] else 0.0
    return result


async def run():
    top_k = 3
    print(f"Running {len(TEST_QUERIES)} labeled queries across {len(CONFIGURATIONS)} configurations (top_k={top_k})...\n")

    all_metrics = {}
    all_labeled_results = {}

    for config_name, search_fn in CONFIGURATIONS.items():
        labeled_results = []
        for query, expected, category in TEST_QUERIES:
            results = await search_fn(query, top_k)
            labeled_results.append((expected, category, results))
        all_labeled_results[config_name] = labeled_results
        all_metrics[config_name] = compute_metrics(labeled_results, top_k)

    categories = sorted({cat for _, _, cat in TEST_QUERIES})

    print("Overall")
    header = f"{'Metric':<16}" + "".join(f"{name:<16}" for name in CONFIGURATIONS)
    print(header)
    print("-" * len(header))
    for metric in (f"recall@{top_k}", "mrr"):
        row = f"{metric:<16}" + "".join(f"{all_metrics[name][metric]:<16.3f}" for name in CONFIGURATIONS)
        print(row)

    print(f"\nMRR by query category ({len(TEST_QUERIES)} queries total across {len(categories)} categories)")
    header = f"{'Category':<16}" + "".join(f"{name:<16}" for name in CONFIGURATIONS)
    print(header)
    print("-" * len(header))
    for cat in categories:
        row = f"{cat:<16}" + "".join(f"{all_metrics[name].get(f'mrr_{cat}', 0.0):<16.3f}" for name in CONFIGURATIONS)
        print(row)

    best_config = max(CONFIGURATIONS, key=lambda name: all_metrics[name]["mrr"])
    print(f"\nQueries where the best configuration ('{best_config}') did not rank the correct document #1:")
    any_failures = False
    for (query, expected, category), (exp2, cat2, results) in zip(TEST_QUERIES, all_labeled_results[best_config]):
        top_title = results[0]["title"] if results else "(no results)"
        if not results or expected.lower() not in results[0].get("title", "").lower():
            any_failures = True
            print(f"  [{category}] '{query}'\n      expected: {expected}  |  got: {top_title}")
    if not any_failures:
        print("  (none)")


if __name__ == "__main__":
    asyncio.run(run())