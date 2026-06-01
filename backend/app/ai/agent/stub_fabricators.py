from __future__ import annotations

from ...core.config import settings
from ...llm.stub import register_fabricator
from .schemas import AdjustedTaskList, SubtopicList


def _fabricate_subtopics(context: dict) -> dict:
    goal = context.get("goal", "the topic")
    return {
        "subtopics": [
            f"Fundamentals of {goal}",
            f"Core concepts of {goal}",
            f"Practical application of {goal}",
        ]
    }


def _fabricate_adjusted_tasks(context: dict) -> dict:
    tasks = context.get("tasks", [])
    budget = float(context.get("hours_budget", 10.0)) * settings.TASKGEN_BUDGET_TOLERANCE
    kept: list[dict] = []
    running = 0.0
    for t in tasks:
        if running + t["estimated_hours"] <= budget:
            kept.append(t)
            running += t["estimated_hours"]
    return {
        "tasks": kept,
        "rationale": "Trimmed tasks to fit within the available hours budget.",
    }


register_fabricator(SubtopicList, _fabricate_subtopics)
register_fabricator(AdjustedTaskList, _fabricate_adjusted_tasks)
