from datetime import date, timedelta

import pytest
from app.ai.task_generation.generator import (
    GenerationResult,
    TaskGenerationError,
    TaskGenerator,
)
from app.ai.task_generation.schemas import PlanContext, TaskDraft, TaskGenerationOutput
from app.ai.task_generation.validator import validate_tasks
from app.llm.base import LLMClient, LLMError


class FakeLLMClient(LLMClient):
    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.calls = 0

    @property
    def model_name(self) -> str:
        return "fake"

    def parse(self, *, system, user, schema, temperature=0.2, context=None):
        out = self._outputs[min(self.calls, len(self._outputs) - 1)]
        self.calls += 1
        if isinstance(out, Exception):
            raise out
        return out


def _ctx(**kwargs) -> PlanContext:
    base = dict(plan_id=1, goal="Learn Python", hours_per_week=10.0)
    base.update(kwargs)
    return PlanContext(**base)


def _tasks(*pairs) -> TaskGenerationOutput:
    return TaskGenerationOutput(
        tasks=[
            TaskDraft(title=t, estimated_hours=h, rationale="relates to goal")
            for t, h in pairs
        ]
    )


def test_valid_batch_passes():
    report = validate_tasks(_tasks(("A", 5), ("B", 6), ("C", 4)).tasks, _ctx())
    assert report.is_valid


def test_empty_batch_fails():
    report = validate_tasks([], _ctx())
    assert not report.is_valid
    assert "at least one" in report.errors[0]



def test_negative_hours_fails():
    report = validate_tasks(_tasks(("A", 5), ("B", 6), ("C", -1)).tasks, _ctx())
    assert any("non-positive" in e for e in report.errors)


def test_hours_below_minimum_fails():
    report = validate_tasks(_tasks(("A", 5), ("B", 6), ("C", 0.1)).tasks, _ctx())
    assert any("unrealistically short" in e for e in report.errors)


def test_per_task_hours_too_large_fails():
    report = validate_tasks(_tasks(("A", 5), ("B", 6), ("C", 40)).tasks, _ctx())
    assert any("unrealistic for a single task" in e for e in report.errors)


def test_total_over_budget_fails():
    report = validate_tasks(
        _tasks(
            ("A", 14), ("B", 14), ("C", 14), ("D", 14),
            ("E", 14), ("F", 14), ("G", 14), ("H", 14),
        ).tasks,
        _ctx(),
    )
    assert any("exceed the remaining budget" in e for e in report.errors)


def test_duplicate_titles_fails():
    report = validate_tasks(_tasks(("A", 5), ("a", 6), ("C", 4)).tasks, _ctx())
    assert any("duplicates" in e for e in report.errors)


def test_missing_rationale_fails():
    out = TaskGenerationOutput(
        tasks=[
            TaskDraft(title="A", estimated_hours=5, rationale="ok"),
            TaskDraft(title="B", estimated_hours=5, rationale="ok"),
            TaskDraft(title="C", estimated_hours=5, rationale="   "),
        ]
    )
    report = validate_tasks(out.tasks, _ctx())
    assert any("missing a rationale" in e for e in report.errors)


def test_uniform_hours_warns():
    out = _tasks(("A", 5), ("B", 5), ("C", 5), ("D", 5), ("E", 5))
    report = validate_tasks(out.tasks, _ctx())
    assert report.is_valid
    assert any("same estimated_hours" in w for w in report.warnings)


def test_varied_hours_no_uniform_warning():
    out = _tasks(("A", 1), ("B", 3), ("C", 5), ("D", 2), ("E", 4))
    report = validate_tasks(out.tasks, _ctx())
    assert not any("same estimated_hours" in w for w in report.warnings)


def test_similar_titles_fails():
    out = TaskGenerationOutput(
        tasks=[
            TaskDraft(title="Review key concepts of distributed systems", estimated_hours=3, rationale="ok"),
            TaskDraft(title="Review fundamental concepts of distributed systems", estimated_hours=3, rationale="ok"),
            TaskDraft(title="Practice designing a URL shortener", estimated_hours=4, rationale="ok"),
        ]
    )
    report = validate_tasks(out.tasks, _ctx())
    assert not report.is_valid
    assert any("too similar" in e for e in report.errors)


def test_distinct_titles_no_similarity_warning():
    out = _tasks(
        ("Study CAP theorem", 2),
        ("Practice designing a URL shortener", 4),
        ("Review load balancing strategies", 3),
    )
    report = validate_tasks(out.tasks, _ctx())
    assert not any("too similar" in w for w in report.warnings)


def test_remaining_budget_deducts_existing_hours():
    ctx = _ctx(existing_hours=30.0)
    assert ctx.hours_budget() == pytest.approx(80.0)
    assert ctx.remaining_budget() == pytest.approx(50.0)


def test_batch_exceeding_remaining_budget_fails():
    ctx = _ctx(existing_hours=70.0)
    report = validate_tasks(_tasks(("A", 5), ("B", 6), ("C", 4)).tasks, ctx)
    assert any("remaining budget" in e for e in report.errors)


def test_batch_within_remaining_budget_passes():
    ctx = _ctx(existing_hours=70.0)
    report = validate_tasks(_tasks(("A", 2), ("B", 2), ("C", 1)).tasks, ctx)
    assert report.is_valid


def test_budget_uses_target_date_when_present():
    ctx = _ctx(target_date=date.today() + timedelta(weeks=4))
    assert ctx.weeks_available() == 4
    assert ctx.hours_budget() == pytest.approx(40.0)


def test_budget_falls_back_to_default_horizon():
    ctx = _ctx()
    assert ctx.weeks_available() == 8


def test_past_due_date_still_has_one_week():
    ctx = _ctx(target_date=date.today() - timedelta(days=3))
    assert ctx.weeks_available() == 1


def test_budget_uses_actual_days_not_rounded_weeks():
    ctx = _ctx(hours_per_week=10.0, target_date=date.today() + timedelta(days=2))
    assert ctx.weeks_available() == 1
    assert ctx.hours_budget() == pytest.approx(10.0 * 2 / 7, rel=1e-3)


def test_weeks_available_and_hours_budget_differ_for_short_deadlines():
    ctx = _ctx(hours_per_week=7.0, target_date=date.today() + timedelta(days=3))
    assert ctx.weeks_available() == 1
    assert ctx.hours_budget() < ctx.hours_per_week


def test_generator_succeeds_first_try():
    client = FakeLLMClient([_tasks(("A", 5), ("B", 6), ("C", 4))])
    result = _generate(client)
    assert isinstance(result, GenerationResult)
    assert result.attempts == 1
    assert len(result.tasks) == 3


def test_generator_retries_then_succeeds():
    bad = _tasks(("A", 999), ("B", 999), ("C", 999))
    good = _tasks(("A", 5), ("B", 6), ("C", 4))
    client = FakeLLMClient([bad, good])
    result = _generate(client)
    assert result.attempts == 2
    assert client.calls == 2


def test_generator_salvages_valid_subset():
    mixed = _tasks(("A", 5), ("B", 6), ("C", 4), ("D", 999))
    client = FakeLLMClient([mixed])
    result = _generate(client)
    assert {t.title for t in result.tasks} == {"A", "B", "C"}
    assert result.warnings


def test_generator_raises_when_nothing_salvageable():
    garbage = _tasks(("A", 0), ("B", -1), ("C", 0))
    client = FakeLLMClient([garbage])
    with pytest.raises(TaskGenerationError):
        _generate(client)


def test_generator_raises_on_persistent_llm_error():
    client = FakeLLMClient([LLMError("boom")])
    with pytest.raises(TaskGenerationError):
        _generate(client)


def test_cross_batch_similar_title_fails():
    existing = ["Review key concepts of distributed systems"]
    new_tasks = _tasks(
        ("Review fundamental concepts of distributed systems", 3),
        ("Practice designing a URL shortener", 4),
        ("Study consensus algorithms", 3),
    )
    report = validate_tasks(new_tasks.tasks, _ctx(), existing_titles=existing)
    assert not report.is_valid
    assert any("overlaps with an already-existing task" in e for e in report.errors)


def test_cross_batch_distinct_title_passes():
    existing = ["Review key concepts of distributed systems"]
    new_tasks = _tasks(
        ("Practice designing a URL shortener", 4),
        ("Study consensus algorithms", 3),
        ("Implement a rate limiter", 3),
    )
    report = validate_tasks(new_tasks.tasks, _ctx(), existing_titles=existing)
    assert report.is_valid


def test_cross_batch_no_existing_titles_passes():
    new_tasks = _tasks(("A", 5), ("B", 6), ("C", 4))
    report = validate_tasks(new_tasks.tasks, _ctx(), existing_titles=None)
    assert report.is_valid


def test_generator_passes_existing_titles_to_validator():
    overlapping = _tasks(
        ("Review fundamental concepts of distributed systems", 3),
        ("Practice designing a URL shortener", 4),
        ("Study consensus algorithms", 3),
    )
    good = _tasks(
        ("Practice designing a URL shortener", 4),
        ("Study consensus algorithms", 3),
        ("Implement a rate limiter", 3),
    )
    client = FakeLLMClient([overlapping, good])
    existing = ["Review key concepts of distributed systems"]
    result = TaskGenerator(client, max_attempts=3).generate(_ctx(), existing_titles=existing)
    assert result.attempts == 2
    assert not any("distributed systems" in t.title for t in result.tasks)


def _generate(client) -> GenerationResult:
    return TaskGenerator(client, max_attempts=2).generate(_ctx())
