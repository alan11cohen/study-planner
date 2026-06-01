from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..ai.task_generation import PlanContext, TaskGenerator
from ..ai.task_generation.generator import TaskGenerationError
from ..core.config import settings
from ..repositories.plan_repository import PlanRepository
from ..repositories.task_repository import TaskRepository
from ..schemas.study_task import StudyTaskCreate, StudyTaskRead
from ..schemas.task_generation import GenerateTasksRequest, GenerateTasksResponse


class TaskGenerationService:
    def __init__(self, db: Session, generator: TaskGenerator) -> None:
        self.plan_repo = PlanRepository(db)
        self.task_repo = TaskRepository(db)
        self.generator = generator

    def generate_tasks(
        self, plan_id: int, req: GenerateTasksRequest
    ) -> GenerateTasksResponse:
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        existing_tasks = [] if req.replace_existing else self.task_repo.get_by_plan_id(plan_id)
        existing_titles = [t.title for t in existing_tasks] or None
        existing_hours = sum(t.estimated_hours for t in existing_tasks)

        ctx = PlanContext(
            plan_id=plan.id,
            goal=plan.goal,
            hours_per_week=plan.hours_per_week,
            description=plan.description,
            target_date=plan.target_date,
            existing_hours=existing_hours,
        )

        min_viable = settings.TASKGEN_MIN_TASKS * settings.TASKGEN_MIN_TASK_HOURS
        remaining = ctx.remaining_budget()
        if remaining < min_viable:
            detail = (
                "Not enough study time available to generate tasks. "
                "This plan has no remaining study hours available before the due date. "
                "Try increasing weekly hours or extending the due date."
            )
            raise HTTPException(status_code=400, detail=detail)

        try:
            result = self.generator.generate(
                ctx,
                count=req.count,
                extra_instructions=req.extra_instructions,
                existing_titles=existing_titles,
            )
        except TaskGenerationError as exc:
            raise HTTPException(
                status_code=502, detail=f"Could not generate valid tasks: {exc}"
            ) from exc

        if req.replace_existing:
            self.task_repo.delete_by_plan_id(plan_id)

        creates = [
            StudyTaskCreate(
                title=draft.title.strip(),
                estimated_hours=round(draft.estimated_hours, 2),
            )
            for draft in result.tasks
        ]
        tasks = self.task_repo.create_many(plan_id, creates)

        return GenerateTasksResponse(
            plan_id=plan_id,
            tasks=[StudyTaskRead.model_validate(t) for t in tasks],
            model=result.model,
            attempts=result.attempts,
            warnings=result.warnings,
        )
