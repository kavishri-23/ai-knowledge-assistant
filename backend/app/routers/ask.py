"""Question answering: /ask (one JSON reply), /ask/stream (live tokens) and /search (debugging)."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.deps import get_services
from app.schemas import AskRequest, AskResponse, SearchRequest, Source
from app.services.container import Services
from app.services.errors import LLMError
from app.services.prompting import NOT_FOUND, build_prompt, extract_citations, is_not_found
from app.services.retrieval import RetrievedChunk

router = APIRouter(tags=["ask"])


def _require_ready(svc: Services, doc_id: str) -> None:
    document = svc.registry.get(doc_id)
    if document is None:
        raise HTTPException(404, "Document not found. Upload it first.")
    if document.status == "failed":
        raise HTTPException(409, document.error or "This document could not be processed.")
    if document.status != "ready":
        raise HTTPException(409, "The document is still being processed. Try again in a moment.")


def _to_sources(chunks: list[RetrievedChunk], cited: list[int] | None = None) -> list[Source]:
    cited = cited or []
    return [
        Source(
            number=number,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            similarity=chunk.similarity,
            text=chunk.text,
            cited=number in cited,
        )
        for number, chunk in enumerate(chunks, start=1)
    ]


def _event(payload: dict) -> str:
    return json.dumps(payload) + "\n"


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, svc: Services = Depends(get_services)):
    _require_ready(svc, request.document_id)
    chunks = svc.retriever.retrieve(request.document_id, request.question)
    if not chunks:  # nothing relevant: do not even call the model
        return AskResponse(answer=NOT_FOUND, grounded=False, sources=[])

    try:
        answer = svc.llm.generate(build_prompt(request.question, chunks))
    except LLMError as error:
        raise HTTPException(502, str(error)) from error

    if is_not_found(answer):
        return AskResponse(answer=answer, grounded=False, sources=[])
    cited = extract_citations(answer, len(chunks))
    return AskResponse(answer=answer, grounded=bool(cited), sources=_to_sources(chunks, cited))


@router.post("/ask/stream")
def ask_stream(request: AskRequest, svc: Services = Depends(get_services)):
    """Newline-delimited JSON events: sources, then tokens, then done (or error)."""
    _require_ready(svc, request.document_id)
    chunks = svc.retriever.retrieve(request.document_id, request.question)
    sources = [source.model_dump() for source in _to_sources(chunks)]

    def events():
        yield _event({"type": "sources", "sources": sources})
        if not chunks:
            yield _event({"type": "token", "text": NOT_FOUND})
            yield _event({"type": "done", "cited": [], "not_found": True})
            return

        parts: list[str] = []
        try:
            for token in svc.llm.stream(build_prompt(request.question, chunks)):
                parts.append(token)
                yield _event({"type": "token", "text": token})
        except LLMError as error:
            yield _event({"type": "error", "message": str(error)})
            return

        answer = "".join(parts)
        yield _event(
            {
                "type": "done",
                "cited": extract_citations(answer, len(chunks)),
                "not_found": is_not_found(answer),
            }
        )

    return StreamingResponse(events(), media_type="application/x-ndjson")


@router.post("/search", response_model=list[Source])
def search(request: SearchRequest, svc: Services = Depends(get_services)):
    """Return the retrieved passages without calling the model (used by the eval script)."""
    _require_ready(svc, request.document_id)
    chunks = svc.retriever.retrieve(request.document_id, request.question, request.mode)
    return _to_sources(chunks)
