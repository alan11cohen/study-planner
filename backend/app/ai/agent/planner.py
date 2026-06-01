from __future__ import annotations

import logging
from datetime import date

from langgraph.graph import END, StateGraph

from ...ai.rag.base import Retriever
from ...ai.task_generation.generator import TaskGenerationError, TaskGenerator
from ...ai.task_generation.schemas import PlanContext
from ...core.config import settings
from ...llm.base import LLMClient
from ...repositories.document_repository import DocumentRepository
from .schemas import AdjustedTaskList, SubtopicList
from .state import PlannerState

_log = logging.getLogger(__name__)


def _decompose_system() -> str:
    mn, mx = settings.AGENT_MIN_SUBTOPICS, settings.AGENT_MAX_SUBTOPICS
    return (
        "You are a study planning expert. Break down the given learning goal into "
        "concrete, distinct subtopics that together cover the goal comprehensively. "
        f"Return between {mn} and {mx} subtopics. Each subtopic must be specific and actionable."
    )

_ADJUST_SYSTEM = (
    "You are a study planning expert. You are given a list of study tasks that "
    "violate certain constraints. Adjust the task list to fix all violations while "
    "preserving coverage of the original goal as much as possible. "
    "You may reduce estimated hours, merge similar tasks, or remove lower-priority tasks."
)


class PlannerGraph:
    def __init__(
        self,
        llm_client: LLMClient,
        task_generator: TaskGenerator,
        retriever: Retriever,
        doc_repo: DocumentRepository,
        max_attempts: int,
    ) -> None:
        self._llm = llm_client
        self._generator = task_generator
        self._retriever = retriever
        self._doc_repo = doc_repo
        self._max_attempts = max_attempts

    def _retrieve_context(self, state: PlannerState) -> dict:
        docs = self._doc_repo.get_by_plan_id(state["plan_id"])
        if not docs:
            return {"rag_context": ""}
        try:
            chunks = self._retriever.retrieve(state["goal"], state["plan_id"])
        except Exception as exc:
            _log.warning("RAG retrieval failed for plan %s: %s", state["plan_id"], exc)
            return {"rag_context": ""}
        if not chunks:
            return {"rag_context": ""}
        context = "\n\n".join(
            f'<document source="{c.filename}">\n{c.text}\n</document>'
            for c in chunks
        )
        return {"rag_context": context}

    def _decompose_goal(self, state: PlannerState) -> dict:
        user_lines = [f"Learning goal: {state['goal']}"]
        if state.get("description"):
            user_lines.append(f"Context: {state['description']}")
        if state["rag_context"]:
            user_lines.append(
                f"\nRelevant material from uploaded documents:\n{state['rag_context']}"
            )
        user_lines.append("\nList the concrete subtopics to study.")

        result = self._llm.parse(
            system=_decompose_system(),
            user="\n".join(user_lines),
            schema=SubtopicList,
            context={"goal": state["goal"]},
        )
        return {"subtopics": result.subtopics}

    def _generate_tasks(self, state: PlannerState) -> dict:
        subtopics_text = "\n".join(f"- {s}" for s in state["subtopics"])
        extra = f"Cover these subtopics in order:\n{subtopics_text}"
        if state["rag_context"]:
            extra += f"\n\nRelevant context from uploaded documents:\n{state['rag_context']}"

        try:
            target = date.fromisoformat(state["target_date"]) if state["target_date"] else None
        except ValueError:
            target = None
        ctx = PlanContext(
            plan_id=state["plan_id"],
            goal=state["goal"],
            hours_per_week=state["hours_per_week"],
            description=state.get("description"),
            target_date=target,
            existing_hours=state["existing_hours"],
        )

        try:
            result = self._generator.generate(
                ctx,
                extra_instructions=extra,
                existing_titles=state["existing_titles"] or None,
            )
            return {
                "tasks": [t.model_dump() for t in result.tasks],
                "warnings": state["warnings"] + result.warnings,
                "attempt": state["attempt"] + 1,
            }
        except TaskGenerationError as exc:
            return {
                "tasks": [],
                "violations": [str(exc)],
                "warnings": state["warnings"] + [f"Generation attempt failed: {exc}"],
                "attempt": state["attempt"] + 1,
            }

    def _validate_constraints(self, state: PlannerState) -> dict:
        tasks = state["tasks"]
        violations: list[str] = []

        if not tasks:
            violations.append("No tasks were generated.")
            return {"violations": violations}

        total_hours = sum(t["estimated_hours"] for t in tasks)
        budget_limit = state["hours_budget"] * settings.TASKGEN_BUDGET_TOLERANCE
        if total_hours > budget_limit:
            violations.append(
                f"Total estimated hours ({total_hours:.1f}h) exceeds the "
                f"available budget ({state['hours_budget']:.1f}h)."
            )
        return {"violations": violations}

    def _adjust_plan(self, state: PlannerState) -> dict:
        tasks_text = "\n".join(
            f"- {t['title']} ({t['estimated_hours']}h): {t['rationale']}"
            for t in state["tasks"]
        )
        violations_text = "\n".join(f"- {v}" for v in state["violations"])

        subtopics_text = "\n".join(f"- {s}" for s in state["subtopics"])
        user_prompt = (
            f"Goal: {state['goal']}\n"
            f"Hours budget: {state['hours_budget']:.1f}h\n\n"
            f"Required subtopics to cover:\n{subtopics_text}\n\n"
            f"Current tasks:\n{tasks_text}\n\n"
            f"Constraint violations to fix:\n{violations_text}\n\n"
            "Adjust the task list to fix all violations while preserving coverage of the required subtopics."
        )

        result = self._llm.parse(
            system=_ADJUST_SYSTEM,
            user=user_prompt,
            schema=AdjustedTaskList,
            context={
                "tasks": state["tasks"],
                "hours_budget": state["hours_budget"],
            },
        )
        return {
            "tasks": [t.model_dump() for t in result.tasks],
            "attempt": state["attempt"] + 1,
            "warnings": state["warnings"] + [
                f"Attempt {state['attempt']}: constraints violated, plan adjusted. "
                f"Reason: {result.rationale}"
            ],
        }

    def _salvage(self, state: PlannerState) -> dict:
        budget_limit = state["hours_budget"] * settings.TASKGEN_BUDGET_TOLERANCE
        kept: list[dict] = []
        running = 0.0
        for t in state["tasks"]:
            if running + t["estimated_hours"] <= budget_limit:
                kept.append(t)
                running += t["estimated_hours"]
        return {
            "tasks": kept,
            "violations": [],
            "warnings": state["warnings"] + [
                f"Agent could not satisfy all constraints after {state['attempt']} "
                f"attempt(s). Persisted {len(kept)} valid task(s) as fallback."
            ],
        }

    def _route(self, state: PlannerState) -> str:
        if not state["violations"]:
            return "done"
        if state["attempt"] >= self._max_attempts:
            return "salvage"
        return "adjust"

    def build(self) -> StateGraph:
        graph: StateGraph = StateGraph(PlannerState)

        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("decompose_goal", self._decompose_goal)
        graph.add_node("generate_tasks", self._generate_tasks)
        graph.add_node("validate_constraints", self._validate_constraints)
        graph.add_node("adjust_plan", self._adjust_plan)
        graph.add_node("salvage", self._salvage)

        graph.set_entry_point("retrieve_context")
        graph.add_edge("retrieve_context", "decompose_goal")
        graph.add_edge("decompose_goal", "generate_tasks")
        graph.add_edge("generate_tasks", "validate_constraints")
        graph.add_conditional_edges(
            "validate_constraints",
            self._route,
            {"done": END, "adjust": "adjust_plan", "salvage": "salvage"},
        )
        graph.add_edge("adjust_plan", "validate_constraints")
        graph.add_edge("salvage", END)

        return graph.compile()
