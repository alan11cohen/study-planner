from __future__ import annotations

from ...core.config import settings
from ...llm.stub import register_fabricator
from .schemas import TaskGenerationOutput

_PHASES = [
    "Fundamentals of",
    "Core concepts of",
    "Hands-on practice with",
    "Deep dive into",
    "Applied project on",
    "Review and self-assessment of",
]


def fabricate_task_generation(context: dict) -> dict:
    goal = (context.get("goal") or "the study goal").strip()
    budget = float(context.get("hours_budget") or 20.0)
    hours_per_week = float(context.get("hours_per_week") or 5.0)
    existing = {t.lower() for t in (context.get("existing_titles") or [])}

    count = context.get("count") or 5
    count = max(settings.TASKGEN_MIN_TASKS, min(int(count), settings.TASKGEN_MAX_TASKS))

    existing_hours = float(context.get("existing_hours") or 0.0)
    remaining = max(0.0, budget - existing_hours)

    max_task_hours = hours_per_week * settings.TASKGEN_MAX_TASK_HOURS_RATIO
    per_task = max(0.5, min(max_task_hours, round((remaining * 0.8) / count, 1)))

    tasks = []
    phase_index = 0
    part = 1
    safety_limit = count * (len(_PHASES) + 1)
    attempts = 0
    while len(tasks) < count and attempts < safety_limit:
        attempts += 1
        if phase_index >= len(_PHASES):
            phase_index = 0
            part += 1
        phase = _PHASES[phase_index]
        phase_index += 1
        suffix = f" (part {part})" if part > 1 else ""
        title = f"{phase} {goal}{suffix}"
        if title.lower() not in existing:
            tasks.append(
                {
                    "title": title,
                    "estimated_hours": per_task,
                    "rationale": f"Advances mastery of the goal: {goal}.",
                }
            )

    return {"tasks": tasks}


register_fabricator(TaskGenerationOutput, fabricate_task_generation)
