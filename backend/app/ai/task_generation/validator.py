from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...core.config import settings
from .schemas import PlanContext, TaskDraft

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to",
    "with", "by", "from", "at", "is", "are", "be", "how", "its",
}


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _is_finite_positive(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def _content_words(title: str) -> set[str]:
    return {w for w in title.lower().split() if w not in _STOPWORDS}


def _overlap_coefficient(a: str, b: str) -> float:
    words_a = _content_words(a)
    words_b = _content_words(b)
    shorter = min(len(words_a), len(words_b))
    if shorter == 0:
        return 0.0
    return len(words_a & words_b) / shorter


def validate_tasks(
    tasks: list[TaskDraft],
    ctx: PlanContext,
    *,
    existing_titles: list[str] | None = None,
) -> ValidationReport:
    report = ValidationReport()

    if not tasks:
        report.errors.append("No tasks were generated; produce at least one task.")
        return report
    if len(tasks) < settings.TASKGEN_MIN_TASKS:
        report.errors.append(
            f"Only {len(tasks)} tasks were generated; produce at least "
            f"{settings.TASKGEN_MIN_TASKS}."
        )
    if len(tasks) > settings.TASKGEN_MAX_TASKS:
        report.errors.append(
            f"{len(tasks)} tasks is too many; produce at most "
            f"{settings.TASKGEN_MAX_TASKS}."
        )

    max_task_hours = ctx.hours_per_week * settings.TASKGEN_MAX_TASK_HOURS_RATIO
    seen_exact: set[str] = set()
    valid_titles: list[tuple[int, str]] = []

    for idx, task in enumerate(tasks, start=1):
        title = task.title.strip()
        if not title:
            report.errors.append(f"Task {idx} has an empty title.")
        elif len(title) > 200:
            report.errors.append(f"Task {idx} title is too long (max 200 chars).")
        else:
            key = title.lower()
            if key in seen_exact:
                report.errors.append(f"Task {idx} duplicates an earlier title: '{title}'.")
            else:
                seen_exact.add(key)
                valid_titles.append((idx, title))

        if not _is_finite_positive(task.estimated_hours):
            report.errors.append(
                f"Task {idx} ('{title}') has non-positive estimated_hours "
                f"({task.estimated_hours}); use a positive number."
            )
        elif task.estimated_hours < settings.TASKGEN_MIN_TASK_HOURS:
            report.errors.append(
                f"Task {idx} ('{title}') estimates {task.estimated_hours}h, which is "
                f"unrealistically short; each task must be at least "
                f"{settings.TASKGEN_MIN_TASK_HOURS}h."
            )
        elif task.estimated_hours > max_task_hours:
            report.errors.append(
                f"Task {idx} ('{title}') estimates {task.estimated_hours}h, which is "
                f"unrealistic for a single task; keep each task under "
                f"{round(max_task_hours, 1)}h."
            )

        if not task.rationale.strip():
            report.errors.append(
                f"Task {idx} ('{title}') is missing a rationale tying it to the goal."
            )

    _check_similar_titles(valid_titles, report)
    if existing_titles:
        _check_cross_batch_similarity(valid_titles, existing_titles, report)

    valid_hours = [t.estimated_hours for t in tasks if _is_finite_positive(t.estimated_hours)]
    _check_uniform_hours(valid_hours, report)

    total = sum(valid_hours)
    remaining = ctx.remaining_budget()
    if total > remaining * settings.TASKGEN_BUDGET_TOLERANCE:
        used_note = (
            f" ({round(ctx.existing_hours, 1)}h already allocated)"
            if ctx.existing_hours > 0
            else ""
        )
        report.errors.append(
            f"Total estimated hours ({round(total, 1)}h) exceed the remaining budget "
            f"of {round(remaining, 1)}h{used_note}. Reduce scope or hours."
        )
    elif total < remaining * 0.4:
        report.warnings.append(
            f"Generated tasks use only {round(total, 1)}h of {round(remaining, 1)}h remaining."
        )

    return report


def _check_similar_titles(
    titles: list[tuple[int, str]], report: ValidationReport
) -> None:
    for i, (idx_a, title_a) in enumerate(titles):
        for idx_b, title_b in titles[i + 1:]:
            if _overlap_coefficient(title_a, title_b) >= 0.6:
                report.errors.append(
                    f"Tasks {idx_a} and {idx_b} are too similar: "
                    f"'{title_a}' / '{title_b}'. Each task must cover a distinct subtopic."
                )


def _check_uniform_hours(hours: list[float], report: ValidationReport) -> None:
    if len(hours) < settings.TASKGEN_MIN_TASKS:
        return
    most_common = max(set(hours), key=hours.count)
    share = hours.count(most_common) / len(hours)
    if share >= 0.6:
        report.warnings.append(
            f"{hours.count(most_common)} of {len(hours)} tasks share the same "
            f"estimated_hours ({most_common}h). Vary estimates to reflect actual "
            "task complexity."
        )


def _check_cross_batch_similarity(
    new_titles: list[tuple[int, str]],
    existing_titles: list[str],
    report: ValidationReport,
) -> None:
    for idx, new_title in new_titles:
        for existing in existing_titles:
            if _overlap_coefficient(new_title, existing) >= 0.6:
                report.errors.append(
                    f"Task {idx} ('{new_title}') overlaps with an already-existing task "
                    f"('{existing}'). Generate a task covering a different subtopic."
                )
                break
