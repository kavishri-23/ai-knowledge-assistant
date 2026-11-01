"""Wires the pieces together. Routes get everything they need from one `Services` object."""

from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.services.embeddings import Embedder
from app.services.llm import OllamaClient
from app.services.registry import Registry
from app.services.retrieval import Retriever
from app.services.vectorstore import ChromaStore, VectorStore


@dataclass
class Services:
    settings: Settings
    registry: Registry
    store: VectorStore
    embedder: Embedder
    retriever: Retriever
    llm: OllamaClient

    def upload_path(self, doc_id: str) -> Path:
        return self.settings.data_path / "uploads" / f"{doc_id}.pdf"


def build_services(settings: Settings) -> Services:
    data = settings.data_path
    (data / "uploads").mkdir(parents=True, exist_ok=True)

    store = ChromaStore(str(data / "chroma_db"))
    embedder = Embedder(settings.embedding_model)
    return Services(
        settings=settings,
        registry=Registry(data / "registry.sqlite3"),
        store=store,
        embedder=embedder,
        retriever=Retriever(
            store,
            embedder,
            top_k=settings.top_k,
            candidate_pool=settings.candidate_pool,
            min_similarity=settings.min_similarity,
        ),
        llm=OllamaClient(settings.ollama_url, settings.ollama_model, settings.ollama_timeout_s),
    )
