from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlanDocumentRead(BaseModel):
    id: int
    plan_id: int
    filename: str
    content_type: str
    size_bytes: int
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    grounded: bool
