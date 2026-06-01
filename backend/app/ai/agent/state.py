from __future__ import annotations

from typing import TypedDict


class PlannerState(TypedDict):
    plan_id: int
    goal: str
    description: str | None
    hours_per_week: float
    hours_budget: float
    existing_titles: list[str]
    target_date: str | None

    existing_hours: float

    rag_context: str
    subtopics: list[str]
    tasks: list[dict]
    violations: list[str]
    warnings: list[str]
    attempt: int
