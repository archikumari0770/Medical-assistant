# MedGraph-RAG

A research prototype of a clinical decision-support system that combines a **medical knowledge graph**, a **modern hybrid RAG pipeline**, and an **LLM narrator**, wrapped in a role-based full-stack application.

> **Not for clinical use.** This project uses synthetic data only. The knowledge graph and the reference corpus were written for this prototype and have **not** been validated by clinicians. Nothing here is a diagnosis, and it must not be used with real patient data without clinical validation, regulatory review, security hardening, and clinician oversight (see [Path to Production](#path-to-production)).

---

## What it does

A doctor enters symptoms (or pastes a free-text note) for a patient. The system:

1. Extracts symptoms from the text, handling simple negation ("denies fever").
2. Queries a **Neo4j knowledge graph** for candidate conditions, ranked by weighted symptom matches.
3. Grounds each candidate with **GraphRAG**: its own reference material plus its graph-known differential neighbours, fetched by exact identity rather than similarity guesses.
4. Checks the patient's own indexed notes (hybrid RAG, strictly scoped per patient) for conflicting history such as "ruled out X".
5. Runs rule-based safety checks: red-flag symptoms, drug interactions, and contraindications against the patient's active medications.
6. Sends the structured result to Claude, which writes a hedged, clinician-facing summary that argues *why* the top candidate is favored over its differentials.

The LLM does **not** rank or retrieve anything. It only narrates results computed upstream.

## Architecture

```
                   ┌──────────────────────────────────────────┐
  Symptoms /       │  FastAPI  (JWT auth, role-based access)  │
  free text  ───►  └───────────────┬──────────────────────────┘
                                   │
        ┌──────────────────────────┼───────────────────────────┐
        ▼                          ▼                           ▼
  Neo4j knowledge graph      Qdrant (hybrid RAG)         PostgreSQL
  26 conditions, 49          dense + sparse vectors      patients, users, labs,
  symptoms, meds,            RRF fusion + reranking      encounters, medications
  interactions,              patient_notes (scoped)
  differentials              medical_knowledge
        │                          │
        └────────► GraphRAG ◄──────┘
                  (graph picks WHAT to fetch,
                   Qdrant supplies the text)
                          │
              scoring · conflict check · safety rules
                          │
                     Claude narrator
```

### Retrieval pipeline

| Stage | Technique |
|---|---|
| Chunking | Recursive split (paragraph → sentence → hard window) with overlap |
| Dense embeddings | `BAAI/bge-small-en-v1.5` via FastEmbed (ONNX, no PyTorch) |
| Sparse embeddings | BM25 (`Qdrant/bm25`) via FastEmbed |
| Fusion | Reciprocal Rank Fusion through Qdrant's Query API |
| Reranking | Cross-encoder (`Xenova/ms-marco-MiniLM-L-6-v2`) over the top 15 fused candidates |
| Contextual Retrieval | Optional LLM-written context blurb per chunk before embedding (needs an Anthropic API key) |
| GraphRAG | Exact, graph-driven document fetch plus `DIFFERENTIAL_OF` contrast evidence |

### Roles

| Role | Can do |
|---|---|
| **Admin** | Create and deactivate staff accounts, change roles, archive/restore/delete patients |
| **Doctor** | Full chart, run analysis, add encounters, upload and search notes |
| **Receptionist** | Register and edit patient demographics only |
| **Lab** | Enter and view lab results only |

IDs are system-generated and sequential (`PT-000001`, `DOC-000001`, `LAB-000001`, ...). Patients are archived rather than erased, and hard deletion is allowed only for records with no clinical history.

## Tech stack

**Backend:** Python 3.10+, FastAPI, SQLAlchemy (async), PostgreSQL, Neo4j, Qdrant, FastEmbed, Anthropic API
**Frontend:** React 18, Vite, React Router
**Infra:** Docker Compose for the three data stores

## Getting started

### Prerequisites

- Python 3.10+, Node.js 18+, Docker Desktop
- An Anthropic API key (needed for the narrator and for Contextual Retrieval; the app degrades gracefully without one, but summaries and context blurbs will be skipped)

### 1. Start the databases

```bash
docker compose up -d
```

Starts PostgreSQL (5432), Neo4j (7474 / 7687) and Qdrant (6333).

### 2. Backend

```bash
cd backend
python -m pip install -r requirements.txt
```

Edit `backend/.env` and set at least `ANTHROPIC_API_KEY` and a strong `JWT_SECRET_KEY`. Then initialise and seed **in this order**:

```bash
python -m scripts.init_postgres          # create tables
python -m scripts.seed_neo4j             # knowledge graph
python -m scripts.seed_users             # demo accounts (one per role)
python -m scripts.seed_medical_knowledge # RAG reference corpus (wipes and reseeds)
python -m scripts.seed_demo              # optional: one synthetic demo patient

uvicorn app.main:app --reload --port 8000
```

API docs are served at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### Demo accounts

Created by `seed_users.py`. **These are for local demos only. Change them before anything else.**

| Role | Email | Password |
|---|---|---|
| Admin | `admin@medgraph.demo` | `admin12345` |
| Doctor | `doctor@medgraph.demo` | `doctor12345` |
| Receptionist | `reception@medgraph.demo` | `reception12345` |
| Lab | `lab@medgraph.demo` | `lab12345` |

## Evaluation

Two scripts measure the retrieval work. Run them after seeding.

```bash
python -m scripts.eval_rag        # 4-way retrieval ablation
python -m scripts.eval_graphrag   # GraphRAG differential-grounding check
```

### Retrieval ablation

53 labeled queries covering all 26 conditions, tagged as `paraphrase`, `exact_term`, or `confusable`, evaluated at top-3.

| Configuration | Recall@3 | MRR |
|---|---|---|
| Dense-only | 1.000 | 0.909 |
| Sparse-only (BM25) | 0.962 | 0.881 |
| Hybrid (RRF) | 0.981 | 0.921 |
| **Hybrid + rerank** | **1.000** | **0.981** |

On the `confusable` category, dense, sparse and hybrid all plateau at MRR 0.964; only reranking reaches 1.000.

### GraphRAG differential grounding

For 12 known confusable condition pairs (e.g. Migraine vs. Tension-Type Headache, Pneumonia vs. Bronchitis), the real pipeline surfaced correct, bidirectional differential evidence grounded in each neighbour's own reference text in **12/12** cases.

### What the evaluation does and does not show

- The corpus and queries were **written by the author** and are small. Treat these numbers as development-scale evidence for the design, not as a benchmark.
- An earlier evaluation on a smaller corpus caught a real failure: embedding retrieval is **blind to negation** (a document saying "unlike X, no high fever" still matched queries about X). That finding motivated both a rewrite of the reference text and the GraphRAG design, which routes around the problem by using explicit graph relationships instead of similarity.
- A separate bug, where reseeding accumulated stale duplicate documents, silently invalidated one evaluation run (recall collapsed to 0.434 across all configurations). The seed script now clears the collection first.

## Known limitations

- **Content is unvalidated.** The 26-condition graph and reference paragraphs are illustrative, not sourced from clinical guidelines.
- **Contextual Retrieval is implemented but unvalidated.** It needs a valid API key; the reported ablation was run without it.
- **Sparse query path needs review.** Queries are encoded with FastEmbed's `embed()` rather than the BM25 model's dedicated `query_embed()`, which likely understates sparse and hybrid performance. Re-run the ablation after fixing.
- **Symptom extraction is keyword matching**, not clinical NLP.
- **Drug interaction data is hand-written**, not from a licensed source.
- **Schema changes are manual.** There are no Alembic migrations yet; `create_all` does not alter existing tables.
- **No automated tests** beyond the two evaluation scripts.

## Path to production

Code alone does not close most of this list.

**Required before any real patient data:**
1. Clinical validation of all medical content by licensed clinicians.
2. Regulatory review (clinical decision support can qualify as Software as a Medical Device, e.g. under FDA or EU MDR).
3. A signed data-processing agreement (such as a HIPAA BAA) before patient data touches any third-party LLM API.
4. Institutional approval, and a defined liability and human-review workflow.

**Engineering work:**
- HTTPS and proper secrets management; httpOnly cookies instead of `localStorage` for the JWT
- Alembic migrations, automated tests, CI
- Rate limiting, monitoring, backups, containerised deployment
- A licensed drug-interaction source and real clinical NLP

## Project structure

```
medgraph-rag/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── api/         auth, admin, patients, documents, analysis, labs
│   │   ├── auth/        JWT, password hashing, role guards
│   │   ├── database/    postgres, neo4j, qdrant (hybrid search)
│   │   ├── decision/    candidate generation, scoring, conflicts
│   │   ├── graph/       schema, Cypher queries, differential reasoning
│   │   ├── llm/         Claude client, prompts, narrator
│   │   ├── models/      SQLAlchemy models and Pydantic schemas
│   │   ├── nlp/         symptom extraction, negation, temporal parsing
│   │   ├── rag/         retriever, contextual retrieval, patient/medical RAG, GraphRAG
│   │   ├── safety/      red flags, medication safety
│   │   ├── services/    shared account-creation logic
│   │   └── utils/       system-generated ID counters
│   └── scripts/         init/seed scripts, eval_rag.py, eval_graphrag.py
└── frontend/
    └── src/
        ├── auth/        context and route guards
        ├── components/  panels for diagnosis, evidence, notes, search
        └── pages/       role-specific dashboards, patient chart, analysis
```

## Disclaimer

This is a research and learning project. Its output is decision support for a clinician to review, never a diagnosis.