import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.container import Services
from app.services.registry import Registry
from app.services.retrieval import Retriever
from tests.fakes import FakeEmbedder, FakeLLM, FakeStore

PAGES = [
    "Photosynthesis converts light energy into chemical energy. It happens in chloroplasts.",
    "The Treaty of Paris was signed in 1783 and ended the American Revolutionary War.",
]


def pdf_bytes(tag: str = "a") -> bytes:
    """Looks like a PDF to the upload checks; the text itself comes from the patched extractor."""
    return b"%PDF-1.4\n% " + tag.encode() + b"\n"


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        data_dir=str(tmp_path),
        max_upload_mb=1,
        chunk_size=90,
        chunk_overlap=20,
        min_similarity=0.3,
    )


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def client(settings, llm, monkeypatch):
    embedder, store = FakeEmbedder(), FakeStore()
    services = Services(
        settings=settings,
        registry=Registry(settings.data_path / "registry.sqlite3"),
        store=store,
        embedder=embedder,
        retriever=Retriever(
            store,
            embedder,
            top_k=settings.top_k,
            candidate_pool=settings.candidate_pool,
            min_similarity=settings.min_similarity,
        ),
        llm=llm,
    )
    monkeypatch.setattr("app.services.ingest.extract_pages", lambda path, max_pages: PAGES)
    with TestClient(create_app(settings, services)) as test_client:
        yield test_client
