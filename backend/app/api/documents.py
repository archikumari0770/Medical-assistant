from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import require_roles
from app.models.user import User, UserRole
from app.rag.patient_rag import index_patient_document, search_patient_documents

router = APIRouter()


class DocumentIn(BaseModel):
    patient_id: uuid.UUID
    title: str
    text: str


class DocumentSearchIn(BaseModel):
    patient_id: uuid.UUID
    query: str
    top_k: int = 5


@router.post("", status_code=201)
async def upload_document(
    payload: DocumentIn,
    user: User = Depends(require_roles(UserRole.doctor)),
):
    """Chunk, embed, and index a free-text patient document (note, discharge
    summary, etc.) into the patient's Qdrant collection for later retrieval."""
    if not payload.text.strip():
        raise HTTPException(400, "Document text is empty")
    doc_id = await index_patient_document(
        patient_id=str(payload.patient_id),
        title=payload.title,
        text=payload.text,
    )
    return {"document_id": doc_id, "status": "indexed"}


@router.post("/search")
async def search_documents(
    payload: DocumentSearchIn,
    user: User = Depends(require_roles(UserRole.doctor)),
):
    """Semantic search over a single patient's own documents."""
    results = await search_patient_documents(
        patient_id=str(payload.patient_id),
        query=payload.query,
        top_k=payload.top_k,
    )
    return {"results": results}
