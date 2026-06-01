import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai.rag.factory import get_retriever
from app.ai.rag.stub import StubRetriever, clear_stub_store
from app.core.database import get_db
from app.llm.factory import get_llm_client
from app.llm.stub import StubLLMClient
from app.main import app

_TEST_DB_URL = "sqlite:///./test.db"
_engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def reset_stub_store():
    clear_stub_store()


@pytest.fixture
def client():
    def _override_db():
        db = _TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_llm_client] = lambda: StubLLMClient()
    app.dependency_overrides[get_retriever] = lambda: StubRetriever()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def plan(client):
    user = client.post("/users", json={"name": "Agent User"}).json()
    return client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Learn Python", "hours_per_week": 10.0},
    ).json()


def test_agent_generate_tasks_returns_tasks(client, plan):
    resp = client.post(
        f"/plans/{plan['id']}/agent-generate-tasks",
        json={"replace_existing": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["plan_id"] == plan["id"]
    assert len(data["tasks"]) > 0
    assert len(data["subtopics"]) > 0
    assert data["attempts"] >= 1
    assert isinstance(data["warnings"], list)


def test_agent_generate_tasks_plan_not_found(client):
    resp = client.post(
        "/plans/9999/agent-generate-tasks",
        json={"replace_existing": False},
    )
    assert resp.status_code == 404


def test_agent_generate_tasks_replace_existing(client, plan):
    client.post(
        f"/plans/{plan['id']}/agent-generate-tasks",
        json={"replace_existing": False},
    )
    resp = client.post(
        f"/plans/{plan['id']}/agent-generate-tasks",
        json={"replace_existing": True},
    )
    assert resp.status_code == 201
    tasks_resp = client.get(f"/plans/{plan['id']}/tasks").json()
    assert len(tasks_resp) == len(resp.json()["tasks"])


def test_agent_generate_tasks_persists_to_db(client, plan):
    resp = client.post(
        f"/plans/{plan['id']}/agent-generate-tasks",
        json={"replace_existing": False},
    )
    assert resp.status_code == 201
    tasks_in_db = client.get(f"/plans/{plan['id']}/tasks").json()
    assert len(tasks_in_db) == len(resp.json()["tasks"])


def test_agent_generate_tasks_insufficient_budget(client):
    user = client.post("/users", json={"name": "Tight Budget"}).json()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    plan = client.post(
        "/plans",
        json={
            "user_id": user["id"],
            "goal": "Learn Rust",
            "hours_per_week": 1.0,
            "target_date": yesterday,
        },
    ).json()
    resp = client.post(
        f"/plans/{plan['id']}/agent-generate-tasks",
        json={"replace_existing": False},
    )
    assert resp.status_code == 400
