from __future__ import annotations

from dataclasses import dataclass, field

from ...core.config import settings
from ...llm.base import LLMClient, LLMError
from . import stub_fabricator  # noqa: F401
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import PlanContext, TaskDraft, TaskGenerationOutput
from .validator import validate_tasks


class TaskGenerationError(RuntimeError):
    pass


@dataclass
class GenerationResult:
    tasks: list[TaskDraft]
    attempts: int
    model: str
    warnings: list[str] = field(default_factory=list)


class TaskGenerator:
    def __init__(self, client: LLMClient, *, max_attempts: int | None = None) -> None:
        self._client = client
        self._max_attempts = max_attempts or settings.TASKGEN_MAX_ATTEMPTS

    def generate(
        self,
        ctx: PlanContext,
        *,
        count: int | None = None,
        extra_instructions: str | None = None,
        existing_titles: list[str] | None = None,
    ) -> GenerationResult:
        stub_context = {
            "goal": ctx.goal,
            "hours_per_week": ctx.hours_per_week,
            "hours_budget": ctx.hours_budget(),
            "existing_hours": ctx.existing_hours,
            "count": count,
            "existing_titles": existing_titles or [],
        }

        previous_errors: list[str] = []
        last_output: TaskGenerationOutput | None = None

        for attempt in range(1, self._max_attempts + 1):
            user_prompt = build_user_prompt(
                ctx,
                count=count,
                extra_instructions=extra_instructions,
                existing_titles=existing_titles,
                previous_errors=previous_errors,
            )
            try:
                output = self._client.parse(
                    system=SYSTEM_PROMPT,
                    user=user_prompt,
                    schema=TaskGenerationOutput,
                    context=stub_context,
                )
            except LLMError as exc:
                previous_errors = [f"Output could not be parsed: {exc}"]
                if attempt == self._max_attempts:
                    raise TaskGenerationError(
                        f"LLM failed to return valid output after {attempt} attempts: {exc}"
                    ) from exc
                continue

            last_output = output
            report = validate_tasks(output.tasks, ctx, existing_titles=existing_titles)
            if report.is_valid:
                return GenerationResult(
                    tasks=output.tasks,
                    attempts=attempt,
                    model=self._client.model_name,
                    warnings=report.warnings,
                )
            previous_errors = report.errors

        return self._salvage(last_output, ctx, existing_titles=existing_titles)

    def _salvage(
        self,
        output: TaskGenerationOutput | None,
        ctx: PlanContext,
        *,
        existing_titles: list[str] | None = None,
    ) -> GenerationResult:
        if output is None or not output.tasks:
            raise TaskGenerationError(
                "Could not generate any valid tasks after all retries."
            )

        max_task_hours = ctx.hours_per_week * settings.TASKGEN_MAX_TASK_HOURS_RATIO
        budget = ctx.hours_budget() * settings.TASKGEN_BUDGET_TOLERANCE

        kept: list[TaskDraft] = []
        seen: set[str] = {t.lower() for t in (existing_titles or [])}
        running = 0.0
        for task in output.tasks:
            title = task.title.strip()
            key = title.lower()
            valid = (
                title
                and key not in seen
                and 0 < task.estimated_hours <= max_task_hours
                and task.rationale.strip()
            )
            if valid and running + task.estimated_hours <= budget:
                kept.append(task)
                seen.add(key)
                running += task.estimated_hours

        if not kept:
            raise TaskGenerationError(
                "Could not generate any valid tasks after all retries."
            )

        return GenerationResult(
            tasks=kept,
            attempts=self._max_attempts,
            model=self._client.model_name,
            warnings=[
                "Validation did not fully pass; persisted the valid subset of "
                f"{len(kept)} task(s) as a fallback."
            ],
        )
