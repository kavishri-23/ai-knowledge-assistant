import pytest

from app.services.errors import IngestError
from app.services.pdf import extract_pages


def make_pdf(pages):
    """Build a tiny but valid PDF with one line of text per page (no libraries needed)."""
    objects = {}
    page_ids = [4 + 2 * i for i in range(len(pages))]
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode()
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    for pid, text in zip(page_ids, pages):
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
        objects[pid] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {pid + 1} 0 R >>"
        ).encode()
        objects[pid + 1] = (
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode() + objects[number] + b"\nendobj\n"
    xref = len(out)
    size = max(objects) + 1
    out += f"xref\n0 {size}\n0000000000 65535 f \n".encode()
    for number in range(1, size):
        out += f"{offsets[number]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def test_extracts_text_from_every_page(tmp_path):
    path = tmp_path / "sample.pdf"
    path.write_bytes(make_pdf(["Hello from page one", "Greetings from page two"]))
    pages = extract_pages(path, max_pages=10)
    assert "page one" in pages[0]
    assert "page two" in pages[1]


def test_rejects_documents_over_the_page_limit(tmp_path):
    path = tmp_path / "long.pdf"
    path.write_bytes(make_pdf(["a", "b", "c"]))
    with pytest.raises(IngestError, match="limit"):
        extract_pages(path, max_pages=2)


def test_corrupted_file_raises_a_friendly_error(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.4 this is not really a pdf")
    with pytest.raises(IngestError):
        extract_pages(path, max_pages=10)
