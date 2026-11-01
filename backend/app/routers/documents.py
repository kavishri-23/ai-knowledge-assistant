"""Upload, list, inspect and delete documents."""

import hashlib
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile

from app.deps import get_services
from app.schemas import DocumentInfo
from app.services import ingest
from app.services.container import Services

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentInfo, status_code=202)
async def upload_document(
    background: BackgroundTasks,
    response: Response,
    file: UploadFile = File(...),
    svc: Services = Depends(get_services),
):
    """Accept a PDF and index it in the background. Poll GET /documents/{id} for progress."""
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a .pdf file.")

    limit = svc.settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"The file is larger than {svc.settings.max_upload_mb} MB.")
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "This file is not a valid PDF.")

    # The id is a hash of the content: the same file is only ever indexed once.
    doc_id = hashlib.sha256(data).hexdigest()[:32]
    existing = svc.registry.get(doc_id)
    if existing is not None and existing.status != "failed":
        response.status_code = 200
        return existing

    path = svc.upload_path(doc_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    svc.registry.upsert_pending(doc_id, filename)
    background.add_task(ingest.process_document, svc, doc_id, filename)
    return svc.registry.get(doc_id)


@router.get("", response_model=list[DocumentInfo])
def list_documents(svc: Services = Depends(get_services)):
    return svc.registry.list()


@router.get("/{doc_id}", response_model=DocumentInfo)
def get_document(doc_id: str, svc: Services = Depends(get_services)):
    document = svc.registry.get(doc_id)
    if document is None:
        raise HTTPException(404, "Document not found.")
    return document


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str, svc: Services = Depends(get_services)):
    document = svc.registry.get(doc_id)
    if document is None:
        raise HTTPException(404, "Document not found.")
    if document.status in ("pending", "processing"):
        raise HTTPException(409, "Wait until processing finishes before deleting this document.")
    svc.store.delete(doc_id)
    svc.retriever.forget(doc_id)
    svc.registry.delete(doc_id)
    svc.upload_path(doc_id).unlink(missing_ok=True)
    return Response(status_code=204)
