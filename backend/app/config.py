"""Application settings, read from environment variables or a .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Language model (Ollama)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout_s: float = 120.0

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # Where the vector database, SQLite registry and temporary uploads live
    data_dir: str = "data"

    # Upload limits
    max_upload_mb: int = 20
    max_pages: int = 300

    # Chunking (characters)
    chunk_size: int = 800
    chunk_overlap: int = 150

    # Retrieval
    top_k: int = 5  # passages sent to the model
    candidate_pool: int = 15  # candidates taken from each search before merging
    min_similarity: float = 0.2  # cosine similarity below this is treated as irrelevant

    # Comma-separated list of browser origins allowed to call the API
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
