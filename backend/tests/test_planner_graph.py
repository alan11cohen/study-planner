from unittest.mock import MagicMock

import pytest

from app.ai.agent.planner import PlannerGraph
from app.ai.agent.state import PlannerState


def _make_graph(max_attempts: int = 3) -> PlannerGraph:
    return PlannerGraph(
        llm_client=MagicMock(),
        task_generator=MagicMock(),
        retriever=MagicMock(),
        doc_repo=MagicMock(),
        max_attempts=max_attempts,
    )


def _state(**overrides) -> PlannerState:
    base: PlannerState = {
        "plan_id": 1,
        "goal": "Learn Python",
        "description": None,
        "hours_per_week": 5.0,
        "hours_budget": 10.0,
        "existing_titles": [],
        "target_date": None,
        "rag_context": "",
        "subtopics": [],
        "tasks": [],
        "violations": [],
        "warnings": [],
        "attempt": 0,
    }
    base.update(overrides)
    return base


def _tasks(*hours: float) -> list[dict]:
    return [
        {"title": f"Task {i+1}", "estimated_hours": h, "rationale": "covers the goal"}
        for i, h in enumerate(hours)
    ]


class TestValidateConstraints:
    def test_empty_tasks_is_violation(self):
        result = _make_graph()._validate_constraints(_state(tasks=[]))
        assert result["violations"] == ["No tasks were generated."]

    def test_within_budget_passes(self):
        result = _make_graph()._validate_constraints(
            _state(tasks=_tasks(3.0, 4.0), hours_budget=10.0)
        )
        assert result["violations"] == []

    def test_over_budget_is_violation(self):
        result = _make_graph()._validate_constraints(
            _state(tasks=_tasks(8.0, 6.0), hours_budget=10.0)
        )
        assert len(result["violations"]) == 1
        assert "14.0h" in result["violations"][0]

    def test_within_tolerance_passes(self):
        result = _make_graph()._validate_constraints(
            _state(tasks=_tasks(6.0, 6.0), hours_budget=10.0)
        )
        assert result["violations"] == []


class TestRoute:
    def test_no_violations_routes_done(self):
        assert _make_graph()._route(_state(violations=[], attempt=1)) == "done"

    def test_violations_below_max_routes_adjust(self):
        assert (
            _make_graph(max_attempts=3)._route(
                _state(violations=["too many hours"], attempt=1)
            )
            == "adjust"
        )

    def test_violations_at_max_routes_salvage(self):
        assert (
            _make_graph(max_attempts=3)._route(
                _state(violations=["too many hours"], attempt=3)
            )
            == "salvage"
        )

    def test_violations_above_max_routes_salvage(self):
        assert (
            _make_graph(max_attempts=3)._route(
                _state(violations=["too many hours"], attempt=5)
            )
            == "salvage"
        )


class TestSalvage:
    def test_keeps_tasks_within_budget(self):
        tasks = _tasks(5.0, 5.0, 5.0)
        result = _make_graph()._salvage(
            _state(tasks=tasks, hours_budget=10.0, attempt=3, warnings=[])
        )
        assert len(result["tasks"]) == 2
        assert sum(t["estimated_hours"] for t in result["tasks"]) <= 10.0 * 1.25

    def test_adds_fallback_warning(self):
        result = _make_graph()._salvage(
            _state(tasks=_tasks(5.0, 5.0, 5.0), hours_budget=10.0, attempt=3, warnings=[])
        )
        assert len(result["warnings"]) == 1
        assert "fallback" in result["warnings"][0]

    def test_clears_violations(self):
        result = _make_graph()._salvage(
            _state(
                tasks=_tasks(3.0),
                hours_budget=10.0,
                attempt=3,
                warnings=[],
                violations=["too many hours"],
            )
        )
        assert result["violations"] == []

    def test_all_tasks_over_budget_returns_empty(self):
        result = _make_graph()._salvage(
            _state(tasks=_tasks(20.0, 20.0), hours_budget=10.0, attempt=3, warnings=[])
        )
        assert result["tasks"] == []
