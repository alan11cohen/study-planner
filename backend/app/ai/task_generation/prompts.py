from __future__ import annotations

from .schemas import PlanContext

SYSTEM_PROMPT = (
    "You are an expert study planner. You break a learning goal into a concrete, "
    "ordered set of study tasks.\n"
    "Hard rules:\n"
    "- Every task MUST be directly derived from and relevant to the stated goal. "
    "Never invent tasks about unrelated topics.\n"
    "- Each task must be specific and actionable (e.g. 'Practice IAM policies and "
    "roles', not 'Study cloud').\n"
    "- Each task must cover a DISTINCT subtopic. Do not generate tasks with "
    "overlapping content or near-identical titles (e.g. 'Review key concepts' and "
    "'Review fundamental concepts' are duplicates — pick one and move on).\n"
    "- estimated_hours must reflect the ACTUAL complexity of that specific task. "
    "Simple tasks (reading, reviewing notes) should take fewer hours than hands-on exercises "
    "and projects. Do NOT assign the same number of hours to every "
    "task — vary them according to real effort required.\n"
    "- The sum of estimated_hours must fit within the available hours budget you "
    "are given.\n"
    "- Provide a short rationale linking each task to the goal.\n"
    "Return ONLY the structured object requested; no prose."
)


def build_user_prompt(
    ctx: PlanContext,
    *,
    count: int | None = None,
    extra_instructions: str | None = None,
    existing_titles: list[str] | None = None,
    previous_errors: list[str] | None = None,
) -> str:
    lines = [
        "Create study tasks for the following plan.",
        "",
        f"Goal: {ctx.goal}",
    ]
    if ctx.description:
        lines.append(f"Context: {ctx.description}")
    lines.append(f"Weekly commitment: {ctx.hours_per_week} hours/week")
    if ctx.target_date:
        lines.append(
            f"Due date: {ctx.target_date.isoformat()} "
            f"(~{ctx.weeks_available()} weeks away)"
        )
    else:
        lines.append(
            f"No due date. Plan over a ~{ctx.weeks_available()}-week horizon."
        )
    remaining = ctx.remaining_budget()
    if ctx.existing_hours > 0:
        lines.append(
            f"Remaining hours budget: ~{round(remaining, 1)} hours "
            f"({round(ctx.hours_budget(), 1)}h total minus {round(ctx.existing_hours, 1)}h already allocated). "
            "Keep the sum of estimated_hours at or below the remaining budget."
        )
    else:
        lines.append(
            f"Total hours budget: ~{round(remaining, 1)} hours. "
            "Keep the sum of estimated_hours at or below this."
        )

    if existing_titles:
        lines.append("")
        lines.append(
            "The following tasks already exist for this plan. Do NOT generate "
            "tasks that duplicate or overlap with them:"
        )
        lines.extend(f"- {title}" for title in existing_titles)

    if count:
        lines.append(f"Produce exactly {count} tasks.")
    if extra_instructions:
        lines.append(f"Additional instructions: {extra_instructions}")

    if previous_errors:
        lines.append("")
        lines.append(
            "Your previous attempt was rejected by validation. Fix ALL of these "
            "issues and try again:"
        )
        lines.extend(f"- {err}" for err in previous_errors)

    return "\n".join(lines)
