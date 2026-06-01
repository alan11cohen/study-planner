import pytest
from app.ai.rag.factory import get_ingester, get_retriever
from app.ai.rag.stub import StubIngester, StubRetriever, clear_stub_store
from app.core.database import get_db
from app.llm.factory import get_llm_client
from app.llm.stub import StubLLMClient
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_TEST_DB_URL = "sqlite:///./test.db"
_engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def reset_store():
    clear_stub_store()


@pytest.fixture
def client():
    def _override_get_db():
        db = _TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_ingester] = lambda: StubIngester()
    app.dependency_overrides[get_retriever] = lambda: StubRetriever()
    app.dependency_overrides[get_llm_client] = lambda: StubLLMClient()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def plan(client):
    user = client.post("/users", json={"name": "Bob"}).json()
    return client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Learn LlamaIndex", "hours_per_week": 5.0},
    ).json()


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake pdf content for testing"


def test_upload_document_returns_201(client, plan):
    resp = client.post(
        f"/plans/{plan['id']}/documents",
        files={"file": ("notes.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "notes.pdf"
    assert data["plan_id"] == plan["id"]
    assert data["chunk_count"] == 1
    assert data["size_bytes"] == len(_pdf_bytes())


def test_upload_document_plan_not_found(client):
    resp = client.post(
        "/plans/9999/documents",
        files={"file": ("notes.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == 404


def test_upload_document_unsupported_type(client, plan):
    resp = client.post(
        f"/plans/{plan['id']}/documents",
        files={"file": ("image.png", b"fake png", "image/png")},
    )
    assert resp.status_code == 415

def test_upload_text_plain_rejected(client, plan):
    resp = client.post(
        f"/plans/{plan['id']}/documents",
        files={"file": ("notes.txt", b"some text", "text/plain")},
    )
    assert resp.status_code == 415


def test_chat_returns_answer(client, plan):
    client.post(
        f"/plans/{plan['id']}/documents",
        files={"file": ("notes.pdf", _pdf_bytes(), "application/pdf")},
    )
    resp = client.post(
        f"/plans/{plan['id']}/documents/chat",
        json={"question": "What is covered in this plan?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert isinstance(data["sources"], list)
    assert isinstance(data["grounded"], bool)


def test_chat_plan_not_found(client):
    resp = client.post(
        "/plans/9999/documents/chat",
        json={"question": "What is this about?"},
    )
    assert resp.status_code == 404


def test_chat_no_documents_returns_ungrounded(client, plan):
    resp = client.post(
        f"/plans/{plan['id']}/documents/chat",
        json={"question": "What is this about?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sources"] == []
    assert data["grounded"] is False


def test_chat_question_too_short(client, plan):
    resp = client.post(
        f"/plans/{plan['id']}/documents/chat",
        json={"question": ""},
    )
    assert resp.status_code == 422
