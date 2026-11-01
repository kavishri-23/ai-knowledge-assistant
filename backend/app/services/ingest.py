"""Background job: PDF -> text -> chunks -> embeddings -> vector store."""

import logging
import time
from typing import TYPE_CHECKING

from app.services.chunking import chunk_pages
from app.services.errors import IngestError
from app.services.pdf import extract_pages

if TYPE_CHECKING:
    from app.services.container import Services

log = logging.getLogger(__name__)


def process_document(svc: "Services", doc_id: str, filename: str) -> None:
    settings = svc.settings
    path = svc.upload_path(doc_id)
    started = time.perf_counter()
    svc.registry.set_status(doc_id, "processing")
    try:
        pages = extract_pages(path, settings.max_pages)
        chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise IngestError("No readable text found. The PDF may be scanned or image-only.")

        # Embed first: if this fails, any previously indexed data is still intact.
        embeddings = svc.embedder.encode([chunk.text for chunk in chunks])
        svc.store.delete(doc_id)
        svc.store.add(doc_id, filename, chunks, embeddings)
        svc.retriever.forget(doc_id)

        svc.registry.set_status(
            doc_id, "ready", total_pages=len(pages), total_chunks=len(chunks)
        )
        log.info(
            "indexed doc=%s pages=%d chunks=%d in %.1fs",
            doc_id, len(pages), len(chunks), time.perf_counter() - started,
        )
    except IngestError as error:
        log.warning("could not index doc=%s: %s", doc_id, error)
        svc.registry.set_status(doc_id, "failed", error=str(error))
    except Exception:
        log.exception("unexpected failure while indexing doc=%s", doc_id)
        svc.registry.set_status(
            doc_id, "failed", error="Unexpected error while processing. Check the server logs."
        )
    finally:
        path.unlink(missing_ok=True)  # keep the extracted text, not the uploaded file
