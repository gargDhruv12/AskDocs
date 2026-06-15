from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


Stage = Literal["queued", "parsing", "classifying", "indexing", "indexed", "failed"]
DocumentOrigin = Literal["sample", "upload"]


class Classification(BaseModel):
    document_type: str
    topics: list[str] = Field(default_factory=list, max_length=8)
    content_characteristics: list[str] = Field(default_factory=list, max_length=8)
    sensitivity: Literal["public", "internal", "confidential", "restricted"]
    language: str
    summary: str
    confidence: float = Field(ge=0, le=1)


class PageRecord(BaseModel):
    page_number: int
    text: str
    image_path: str
    tables: list[list[list[str | None]]] = Field(default_factory=list)


class DocumentRecord(BaseModel):
    id: str
    workspace_id: str
    name: str
    storage_path: str
    mime_type: str
    origin: DocumentOrigin = "upload"
    status: Stage = "queued"
    progress: int = 0
    page_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str | None = None
    classification: Classification | None = None
    pages: list[PageRecord] = Field(default_factory=list)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatTurn] = Field(min_length=1, max_length=30)


class SearchPlan(BaseModel):
    intent: str
    search_queries: list[str] = Field(min_length=1, max_length=4)
    requires_comparison: bool = False


class Citation(BaseModel):
    id: str
    document_id: str
    document_name: str
    page_number: int
    excerpt: str
    image_url: str


class ChatResponse(BaseModel):
    id: str
    role: Literal["assistant"] = "assistant"
    content: str
    citations: list[Citation] = Field(default_factory=list)


class DocumentPage(BaseModel):
    page_number: int
    image_url: str


class DocumentPagesResponse(BaseModel):
    document_id: str
    document_name: str
    page_count: int
    pages: list[DocumentPage]
