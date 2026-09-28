"""
FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import admin, analysis, auth, documents, labs, patients
from app.database.neo4j import close_driver, verify_connectivity
from app.database.postgres import init_postgres
from app.database.qdrant import ensure_collections


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: initializing Postgres tables...")
    await init_postgres()

    logger.info("Checking Neo4j connectivity...")
    ok = await verify_connectivity()
    logger.info(f"Neo4j reachable: {ok}")

    logger.info("Ensuring Qdrant collections exist...")
    await ensure_collections()

    yield

    logger.info("Shutting down: closing Neo4j driver...")
    await close_driver()


app = FastAPI(
    title="MedGraph-RAG",
    description=(
        "Research prototype clinical decision-support API. "
        "Uses synthetic/de-identified data only. Not for real clinical use "
        "without validation, security review, and clinician oversight."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(labs.router, prefix="/api/labs", tags=["labs"])


@app.get("/health")
async def health():
    return {"status": "ok"}