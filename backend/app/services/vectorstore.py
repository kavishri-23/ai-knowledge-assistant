"""Vector storage. `ChromaStore` is the real one; tests use an in-memory fake."""

from dataclasses import dataclass
from typing import Protocol

from app.services.chunking import Chunk


@dataclass(frozen=True)
class StoredChunk:
    id: str
    text: str
    page_start: int
    page_end: int
    index: int


class VectorStore(Protocol):
    def add(
        self, doc_id: str, filename: str, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> None: ...

    def delete(self, doc_id: str) -> None: ...

    def get_chunks(self, doc_id: str) -> list[StoredChunk]: ...

    def query_ids(self, doc_id: str, embedding: list[float], n: int) -> list[str]: ...

    def embeddings_for(self, ids: list[str]) -> dict[str, list[float]]: ...


class ChromaStore:
    """ChromaDB-backed store. Every chunk carries its document id, so searches stay per-document."""

    _BATCH = 500

    def __init__(self, path: str):
        import chromadb  # imported here so tests and CI do not need chromadb installed

        client = chromadb.PersistentClient(path=path)
        self._collection = client.get_or_create_collection("knowledge_base_v2")

    def add(
        self, doc_id: str, filename: str, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> None:
        ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "doc_id": doc_id,
                "filename": filename,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "chunk_index": i,
            }
            for i, chunk in enumerate(chunks)
        ]
        for start in range(0, len(ids), self._BATCH):
            end = start + self._BATCH
            self._collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
            )

    def delete(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})

    def get_chunks(self, doc_id: str) -> list[StoredChunk]:
        result = self._collection.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
        chunks = [
            StoredChunk(
                id=chunk_id,
                text=text,
                page_start=int(meta["page_start"]),
                page_end=int(meta["page_end"]),
                index=int(meta["chunk_index"]),
            )
            for chunk_id, text, meta in zip(result["ids"], result["documents"], result["metadatas"])
        ]
        return sorted(chunks, key=lambda chunk: chunk.index)

    def query_ids(self, doc_id: str, embedding: list[float], n: int) -> list[str]:
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=n,
            where={"doc_id": doc_id},
            include=["distances"],
        )
        return list(result["ids"][0])

    def embeddings_for(self, ids: list[str]) -> dict[str, list[float]]:
        if not ids:
            return {}
        result = self._collection.get(ids=list(ids), include=["embeddings"])
        embeddings = result.get("embeddings")
        if embeddings is None:
            return {}
        return {
            chunk_id: [float(value) for value in vector]
            for chunk_id, vector in zip(result["ids"], embeddings)
        }
