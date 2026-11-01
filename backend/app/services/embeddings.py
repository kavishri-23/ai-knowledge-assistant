"""Sentence embeddings. The model loads on first use so the server starts quickly."""

import logging
import threading

log = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    log.info("loading embedding model %s", self._model_name)
                    self._model = SentenceTransformer(self._model_name)
        return self._model

    def warm_up(self) -> None:
        try:
            self._get_model()
        except Exception:  # a failed warm-up must never crash the server
            log.exception("could not pre-load the embedding model")

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return unit-length vectors, so cosine similarity is just a dot product."""
        if not texts:
            return []
        vectors = self._get_model().encode(
            texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False
        )
        return vectors.tolist()
