"""Request and response models for the API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

DocumentStatus = Literal["pending", "processing", "ready", "failed"]
SearchMode = Literal["hybrid", "vector", "keyword"]


class DocumentInfo(BaseModel):
    id: str
    filename: str
    status: DocumentStatus
    total_pages: int | None = None
    total_chunks: int | None = None
    error: str | None = None
    created_at: str


class AskRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=1, max_length=1000)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("The question must not be blank.")
        return value


class SearchRequest(AskRequest):
    mode: SearchMode = "hybrid"


class Source(BaseModel):
    number: int  # matches the [n] markers in the answer
    page_start: int
    page_end: int
    similarity: float
    text: str
    cited: bool = False


class AskResponse(BaseModel):
    answer: str
    grounded: bool  # True when the answer cites at least one source
    sources: list[Source]
