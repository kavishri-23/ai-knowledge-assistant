"""PDF text extraction."""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.services.errors import IngestError


def extract_pages(path: Path, max_pages: int) -> list[str]:
    """Return the text of every page ('' for pages without a text layer)."""
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise IngestError("This PDF is password protected. Remove the password and retry.")
        if len(reader.pages) > max_pages:
            raise IngestError(f"This PDF has {len(reader.pages)} pages; the limit is {max_pages}.")
        return [page.extract_text() or "" for page in reader.pages]
    except PyPdfError as error:
        raise IngestError("This file could not be read as a PDF. It may be corrupted.") from error
