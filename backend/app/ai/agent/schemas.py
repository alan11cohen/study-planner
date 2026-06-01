from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ...core.config import settings
from ..task_generation.schemas import TaskDraft


class SubtopicList(BaseModel):
    subtopics: list[str] = Field(
        description="Concrete, distinct subtopics that together cover the goal."
    )

    @field_validator("subtopics")
    @classmethod
    def validate_count(cls, v: list[str]) -> list[str]:
        mn, mx = settings.AGENT_MIN_SUBTOPICS, settings.AGENT_MAX_SUBTOPICS
        if len(v) < mn:
            raise ValueError(f"Expected at least {mn} subtopics, got {len(v)}.")
        if len(v) > mx:
            raise ValueError(f"Expected at most {mx} subtopics, got {len(v)}.")
        return v


class AdjustedTaskList(BaseModel):
    tasks: list[TaskDraft] = Field(
        description="Adjusted task list that satisfies all stated constraints."
    )
    rationale: str = Field(
        description="Brief explanation of what was changed and why."
    )
