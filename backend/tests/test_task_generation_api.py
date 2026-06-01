import pytest
from app.ai.task_generation import TaskGenerator
from app.api.deps import get_task_generation_service
from app.core.database import get_db
from app.llm.stub import StubLLMClient
from app.main import app
from app.services.task_generation_service import TaskGenerationService
from fastapi import Depends
from sqlalchemy.orm import Session


@pytest.fixture
def client_stub(client):
    def _override(db: Session = Depends(get_db)):
        return TaskGenerationService(db, TaskGenerator(StubLLMClient()))

    app.dependency_overrides[get_task_generation_service] = _override
    yield client
    app.dependency_overrides.pop(get_task_generation_service, None)


@pytest.fixture
def plan(client):
    user = client.post("/users", json={"name": "Bob"}).json()
    return client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Learn Rust", "hours_per_week": 8.0},
    ).json()


def test_generate_tasks_persists(client_stub, plan):
    resp = client_stub.post(f"/plans/{plan['id']}/generate-tasks", json={})
    assert resp.status_code == 201
    body = resp.json()
    assert body["plan_id"] == plan["id"]
    assert len(body["tasks"]) >= 3
    assert body["model"] == "stub-offline"
    assert body["attempts"] >= 1
    for task in body["tasks"]:
        assert task["plan_id"] == plan["id"]
        assert task["estimated_hours"] > 0
        assert task["completed"] is False
    listed = client_stub.get(f"/plans/{plan['id']}/tasks").json()
    assert len(listed) == len(body["tasks"])


def test_generate_tasks_respects_count(client_stub, plan):
    resp = client_stub.post(
        f"/plans/{plan['id']}/generate-tasks", json={"count": 4}
    )
    assert resp.status_code == 201
    assert len(resp.json()["tasks"]) == 4


def test_generate_tasks_replace_existing(client_stub, plan):
    client_stub.post(
        f"/plans/{plan['id']}/tasks",
        json={"title": "Old manual task", "estimated_hours": 2.0},
    )
    resp = client_stub.post(
        f"/plans/{plan['id']}/generate-tasks", json={"replace_existing": True}
    )
    assert resp.status_code == 201
    titles = {t["title"] for t in client_stub.get(f"/plans/{plan['id']}/tasks").json()}
    assert "Old manual task" not in titles


def test_generate_tasks_appends_without_replace(client_stub, plan):
    client_stub.post(
        f"/plans/{plan['id']}/tasks",
        json={"title": "Old manual task", "estimated_hours": 2.0},
    )
    resp = client_stub.post(f"/plans/{plan['id']}/generate-tasks", json={})
    generated = len(resp.json()["tasks"])
    listed = client_stub.get(f"/plans/{plan['id']}/tasks").json()
    assert len(listed) == generated + 1


def test_generate_tasks_plan_not_found(client_stub):
    resp = client_stub.post("/plans/9999/generate-tasks", json={})
    assert resp.status_code == 404


def test_generate_tasks_insufficient_budget_returns_400(client_stub, client):
    user = client.post("/users", json={"name": "Carol"}).json()
    plan = client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Quick task", "hours_per_week": 1.0,
              "target_date": "2026-06-01"},
    ).json()
    client.post(
        f"/plans/{plan['id']}/tasks",
        json={"title": "Existing task", "estimated_hours": 1.0},
    )
    resp = client_stub.post(f"/plans/{plan['id']}/generate-tasks", json={})
    assert resp.status_code == 400
    assert "study time" in resp.json()["detail"]


def test_generate_tasks_passes_existing_titles_to_generator(client_stub, plan):
    client_stub.post(
        f"/plans/{plan['id']}/tasks",
        json={"title": "Fundamentals of Learn Rust", "estimated_hours": 2.0},
    )
    resp = client_stub.post(f"/plans/{plan['id']}/generate-tasks", json={})
    assert resp.status_code == 201
    titles = [t["title"] for t in resp.json()["tasks"]]
    assert "Fundamentals of Learn Rust" not in titles
