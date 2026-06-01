from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from ...core.config import settings


class PlanContext(BaseModel):
    plan_id: int
    goal: str
    hours_per_week: float
    description: str | None = None
    target_date: date | None = None
    existing_hours: float = 0.0

    def weeks_available(self, *, today: date | None = None) -> int:
        if self.target_date is None:
            return settings.TASKGEN_DEFAULT_HORIZON_WEEKS
        today = today or date.today()
        days = (self.target_date - today).days
        return max(1, round(days / 7))

    def hours_budget(self, *, today: date | None = None) -> float:
        if self.target_date is None:
            return self.hours_per_week * settings.TASKGEN_DEFAULT_HORIZON_WEEKS
        today = today or date.today()
        days = max(1, (self.target_date - today).days)
        return self.hours_per_week * (days / 7)

    def remaining_budget(self, *, today: date | None = None) -> float:
        return max(0.0, self.hours_budget(today=today) - self.existing_hours)


class TaskDraft(BaseModel):
    title: str = Field(description="Concrete, actionable study task title.")
    estimated_hours: float = Field(
        description="Realistic estimate of focused hours to complete this task."
    )
    rationale: str = Field(
        description="One sentence explaining how this task advances the plan goal."
    )


class TaskGenerationOutput(BaseModel):
    tasks: list[TaskDraft]
