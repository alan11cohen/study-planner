from __future__ import annotations

from pydantic import BaseModel

from .study_task import StudyTaskRead


class AgentGenerateRequest(BaseModel):
    replace_existing: bool = False


class AgentGenerateResponse(BaseModel):
    plan_id: int
    tasks: list[StudyTaskRead]
    subtopics: list[str]
    attempts: int
    warnings: list[str]
