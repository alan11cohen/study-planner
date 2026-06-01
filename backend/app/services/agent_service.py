from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..ai.agent import PlannerGraph, PlannerState
from ..ai.rag.base import Retriever
from ..ai.task_generation import PlanContext, TaskGenerator
from ..core.config import settings
from ..llm.base import LLMClient
from ..repositories.document_repository import DocumentRepository
from ..repositories.plan_repository import PlanRepository
from ..repositories.task_repository import TaskRepository
from ..schemas.agent import AgentGenerateRequest, AgentGenerateResponse
from ..schemas.study_task import StudyTaskCreate, StudyTaskRead


class AgentService:
    def __init__(self, db: Session, llm: LLMClient, retriever: Retriever) -> None:
        self._plan_repo = PlanRepository(db)
        self._task_repo = TaskRepository(db)
        self._doc_repo = DocumentRepository(db)
        self._llm = llm
        self._retriever = retriever

    def run(self, plan_id: int, req: AgentGenerateRequest) -> AgentGenerateResponse:
        plan = self._plan_repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        existing_tasks = (
            [] if req.replace_existing else self._task_repo.get_by_plan_id(plan_id)
        )
        existing_titles = [t.title for t in existing_tasks]
        existing_hours = sum(t.estimated_hours for t in existing_tasks)

        ctx = PlanContext(
            plan_id=plan.id,
            goal=plan.goal,
            hours_per_week=plan.hours_per_week,
            description=plan.description,
            target_date=plan.target_date,
            existing_hours=existing_hours,
        )

        hours_budget = ctx.remaining_budget()
        min_viable = settings.TASKGEN_MIN_TASKS * settings.TASKGEN_MIN_TASK_HOURS
        if hours_budget < min_viable:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Not enough study time available to generate tasks. "
                    "Try increasing weekly hours or extending the due date."
                ),
            )

        generator = TaskGenerator(self._llm, max_attempts=settings.TASKGEN_MAX_ATTEMPTS)
        planner = PlannerGraph(
            llm_client=self._llm,
            task_generator=generator,
            retriever=self._retriever,
            doc_repo=self._doc_repo,
            max_attempts=settings.AGENT_MAX_ATTEMPTS,
        )

        initial_state: PlannerState = {
            "plan_id": plan.id,
            "goal": plan.goal,
            "description": plan.description,
            "hours_per_week": plan.hours_per_week,
            "hours_budget": hours_budget,
            "existing_titles": existing_titles,
            "existing_hours": existing_hours,
            "target_date": plan.target_date.isoformat() if plan.target_date else None,
            "rag_context": "",
            "subtopics": [],
            "tasks": [],
            "violations": [],
            "warnings": [],
            "attempt": 0,
        }

        graph = planner.build()
        final_state: PlannerState = graph.invoke(initial_state)

        if not final_state["tasks"]:
            raise HTTPException(
                status_code=502,
                detail="Agent could not generate any valid tasks after all attempts.",
            )

        if req.replace_existing:
            self._task_repo.delete_by_plan_id(plan_id)

        creates = [
            StudyTaskCreate(
                title=t["title"].strip(),
                estimated_hours=round(t["estimated_hours"], 2),
            )
            for t in final_state["tasks"]
        ]
        saved = self._task_repo.create_many(plan_id, creates)

        return AgentGenerateResponse(
            plan_id=plan_id,
            tasks=[StudyTaskRead.model_validate(t) for t in saved],
            subtopics=final_state["subtopics"],
            attempts=final_state["attempt"],
            warnings=final_state["warnings"],
        )
