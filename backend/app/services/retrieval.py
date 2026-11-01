"""Hybrid retrieval: vector search + keyword (BM25) search, merged with rank fusion.

The merged candidates are then filtered by cosine similarity, so passages that are
unrelated to the question never reach the language model.
"""

from dataclasses import dataclass

from app.services.bm25 import BM25, tokenize
from app.services.vectorstore import StoredChunk

_MAX_CACHED_DOCUMENTS = 20


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    page_start: int
    page_end: int
    similarity: float


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Merge several ranked id lists. An id near the top of any list scores well."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for position, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + position)
    return scores


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class Retriever:
    def __init__(
        self, store, embedder, *, top_k: int, candidate_pool: int, min_similarity: float
    ):
        self._store = store
        self._embedder = embedder
        self._top_k = top_k
        self._pool = candidate_pool
        self._min_similarity = min_similarity
        self._cache: dict[str, tuple[list[StoredChunk], BM25]] = {}

    def forget(self, doc_id: str) -> None:
        """Drop the cached keyword index (call after a document is re-indexed or deleted)."""
        self._cache.pop(doc_id, None)

    def _index(self, doc_id: str) -> tuple[list[StoredChunk], BM25]:
        cached = self._cache.get(doc_id)
        if cached is not None:
            return cached
        chunks = self._store.get_chunks(doc_id)
        index = (chunks, BM25([tokenize(chunk.text) for chunk in chunks]))
        if chunks:
            if len(self._cache) >= _MAX_CACHED_DOCUMENTS:
                self._cache.pop(next(iter(self._cache)))
            self._cache[doc_id] = index
        return index

    def retrieve(self, doc_id: str, question: str, mode: str = "hybrid") -> list[RetrievedChunk]:
        """Return up to `top_k` relevant passages, best first. May return an empty list."""
        chunks, bm25 = self._index(doc_id)
        if not chunks:
            return []
        by_id = {chunk.id: chunk for chunk in chunks}
        query_vector = self._embedder.encode([question])[0]
        pool = min(self._pool, len(chunks))

        rankings: list[list[str]] = []
        if mode in ("hybrid", "vector"):
            rankings.append(self._store.query_ids(doc_id, query_vector, pool))
        if mode in ("hybrid", "keyword"):
            hits = bm25.top(tokenize(question), pool)
            rankings.append([chunks[i].id for i in hits])

        fused = reciprocal_rank_fusion(rankings)
        if not fused:
            return []
        vectors = self._store.embeddings_for(list(fused))

        results: list[RetrievedChunk] = []
        for chunk_id, _ in sorted(fused.items(), key=lambda item: item[1], reverse=True):
            vector = vectors.get(chunk_id)
            if vector is None:
                continue
            similarity = dot(query_vector, vector)
            if similarity < self._min_similarity:
                continue
            chunk = by_id[chunk_id]
            results.append(
                RetrievedChunk(chunk.text, chunk.page_start, chunk.page_end, round(similarity, 3))
            )
            if len(results) >= self._top_k:
                break
        return results
