"""Small in-memory stand-ins so tests run without Chroma, torch or Ollama."""

import hashlib
import math
import re

from app.services.errors import LLMError
from app.services.vectorstore import StoredChunk


def _dot(left, right):
    return sum(a * b for a, b in zip(left, right))


class FakeEmbedder:
    """Hashes words into 64 buckets. Texts that share words get similar vectors."""

    DIM = 64

    def encode(self, texts):
        return [self._vector(text) for text in texts]

    def _vector(self, text):
        vector = [0.0] * self.DIM
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.DIM
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class FakeStore:
    def __init__(self):
        self._rows = {}

    def add(self, doc_id, filename, chunks, embeddings):
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            self._rows[f"{doc_id}:{index}"] = {
                "doc_id": doc_id,
                "chunk": chunk,
                "embedding": embedding,
                "index": index,
            }

    def delete(self, doc_id):
        self._rows = {k: v for k, v in self._rows.items() if v["doc_id"] != doc_id}

    def get_chunks(self, doc_id):
        rows = [(key, row) for key, row in self._rows.items() if row["doc_id"] == doc_id]
        chunks = [
            StoredChunk(
                key, r["chunk"].text, r["chunk"].page_start, r["chunk"].page_end, r["index"]
            )
            for key, r in rows
        ]
        return sorted(chunks, key=lambda chunk: chunk.index)

    def query_ids(self, doc_id, embedding, n):
        scored = [
            (_dot(embedding, row["embedding"]), key)
            for key, row in self._rows.items()
            if row["doc_id"] == doc_id
        ]
        scored.sort(reverse=True)
        return [key for _, key in scored[:n]]

    def embeddings_for(self, ids):
        return {key: self._rows[key]["embedding"] for key in ids if key in self._rows}


class FakeLLM:
    def __init__(self, answer="The war ended with the Treaty of Paris [1].", fail=False):
        self.answer = answer
        self.fail = fail
        self.calls = 0

    def ping(self):
        return True

    def generate(self, prompt):
        self.calls += 1
        if self.fail:
            raise LLMError("Could not connect to Ollama.")
        return self.answer

    def stream(self, prompt):
        self.calls += 1
        if self.fail:
            raise LLMError("Could not connect to Ollama.")
        for word in self.answer.split(" "):
            yield word + " "
