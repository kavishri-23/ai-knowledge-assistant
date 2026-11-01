import json

from app.services.errors import IngestError
from tests.conftest import pdf_bytes


def upload(client, name="notes.pdf", content=None):
    content = pdf_bytes() if content is None else content
    return client.post("/documents", files={"file": (name, content, "application/pdf")})


def upload_ready(client):
    response = upload(client)
    assert response.status_code == 202
    doc_id = response.json()["id"]
    # TestClient finishes background tasks before returning, so the document is ready now.
    assert client.get(f"/documents/{doc_id}").json()["status"] == "ready"
    return doc_id


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "ollama_reachable": True}


def test_upload_indexes_the_document(client):
    doc_id = upload_ready(client)
    info = client.get(f"/documents/{doc_id}").json()
    assert info["filename"] == "notes.pdf"
    assert info["total_pages"] == 2
    assert info["total_chunks"] >= 2
    assert [doc["id"] for doc in client.get("/documents").json()] == [doc_id]


def test_uploading_the_same_file_twice_reuses_the_document(client):
    first = upload(client)
    second = upload(client)
    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(client.get("/documents").json()) == 1


def test_upload_validation(client):
    assert upload(client, name="notes.txt").status_code == 400
    assert upload(client, content=b"").status_code == 400
    assert upload(client, content=b"hello, not a pdf").status_code == 400
    too_big = b"%PDF" + b"0" * (1024 * 1024 + 10)
    assert upload(client, content=too_big).status_code == 413


def test_failed_processing_is_reported(client, monkeypatch):
    def boom(path, max_pages):
        raise IngestError("No readable text found.")

    monkeypatch.setattr("app.services.ingest.extract_pages", boom)
    doc_id = upload(client).json()["id"]
    info = client.get(f"/documents/{doc_id}").json()
    assert info["status"] == "failed"
    assert info["error"] == "No readable text found."
    asked = client.post("/ask", json={"document_id": doc_id, "question": "anything?"})
    assert asked.status_code == 409


def test_ask_returns_answer_with_cited_sources(client):
    doc_id = upload_ready(client)
    question = "What ended the American Revolutionary War?"
    response = client.post("/ask", json={"document_id": doc_id, "question": question})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"].endswith("[1].")
    assert body["grounded"] is True
    assert body["sources"][0]["page_start"] == 2
    assert body["sources"][0]["cited"] is True


def test_unrelated_question_does_not_call_the_model(client, llm):
    doc_id = upload_ready(client)
    response = client.post("/ask", json={"document_id": doc_id, "question": "zzzz qqqq xxxx"})
    assert response.status_code == 200
    assert response.json()["grounded"] is False
    assert response.json()["sources"] == []
    assert llm.calls == 0


def test_ask_error_cases(client, llm):
    assert client.post("/ask", json={"document_id": "nope", "question": "hi?"}).status_code == 404

    client.app.state.services.registry.upsert_pending("pending-doc", "slow.pdf")
    pending = client.post("/ask", json={"document_id": "pending-doc", "question": "hi?"})
    assert pending.status_code == 409

    doc_id = upload_ready(client)
    assert client.post("/ask", json={"document_id": doc_id, "question": "   "}).status_code == 422

    llm.fail = True
    question = "What ended the American Revolutionary War?"
    failed = client.post("/ask", json={"document_id": doc_id, "question": question})
    assert failed.status_code == 502
    assert "Ollama" in failed.json()["detail"]


def test_streaming_sends_sources_tokens_then_done(client):
    doc_id = upload_ready(client)
    response = client.post(
        "/ask/stream",
        json={"document_id": doc_id, "question": "What ended the American Revolutionary War?"},
    )
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines() if line]
    assert events[0]["type"] == "sources" and events[0]["sources"]
    assert events[-1] == {"type": "done", "cited": [1], "not_found": False}
    text = "".join(event["text"] for event in events if event["type"] == "token")
    assert text.strip() == "The war ended with the Treaty of Paris [1]."


def test_streaming_reports_model_errors_as_events(client, llm):
    doc_id = upload_ready(client)
    llm.fail = True
    response = client.post(
        "/ask/stream",
        json={"document_id": doc_id, "question": "What ended the American Revolutionary War?"},
    )
    events = [json.loads(line) for line in response.text.splitlines() if line]
    assert events[-1]["type"] == "error"


def test_search_supports_each_mode(client):
    doc_id = upload_ready(client)
    for mode in ("hybrid", "vector", "keyword"):
        response = client.post(
            "/search",
            json={"document_id": doc_id, "question": "American Revolutionary War", "mode": mode},
        )
        assert response.status_code == 200
        assert response.json()[0]["page_start"] == 2


def test_delete_removes_the_document(client):
    doc_id = upload_ready(client)
    assert client.delete(f"/documents/{doc_id}").status_code == 204
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.delete(f"/documents/{doc_id}").status_code == 404
    assert client.get("/documents").json() == []
