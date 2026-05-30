import pytest


@pytest.fixture
def user(client):
    return client.post("/users", json={"name": "Alice"}).json()


def test_create_plan(client, user):
    response = client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Learn Python", "hours_per_week": 10.0},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["goal"] == "Learn Python"
    assert data["user_id"] == user["id"]
    assert isinstance(data["id"], int)


def test_create_plan_defaults_description_and_target_date_to_null(client, user):
    response = client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Learn Python", "hours_per_week": 10.0},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["description"] is None
    assert data["target_date"] is None


def test_create_plan_with_description_and_target_date(client, user):
    response = client.post(
        "/plans",
        json={
            "user_id": user["id"],
            "goal": "Learn FastAPI",
            "hours_per_week": 5.0,
            "description": "Focus on auth and testing",
            "target_date": "2026-06-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Focus on auth and testing"
    assert data["target_date"] == "2026-06-01"


def test_get_plan(client, user):
    created = client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Learn Python", "hours_per_week": 10.0},
    ).json()
    response = client.get(f"/plans/{created['id']}")
    assert response.status_code == 200
    assert response.json()["goal"] == "Learn Python"


def test_get_plan_not_found(client):
    response = client.get("/plans/999")
    assert response.status_code == 404


def test_get_user_plans(client, user):
    client.post(
        "/plans", json={"user_id": user["id"], "goal": "Goal A", "hours_per_week": 5.0}
    )
    client.post(
        "/plans", json={"user_id": user["id"], "goal": "Goal B", "hours_per_week": 3.0}
    )
    response = client.get(f"/users/{user['id']}/plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 2
    assert {p["goal"] for p in plans} == {"Goal A", "Goal B"}


def test_create_plan_user_not_found(client):
    response = client.post(
        "/plans",
        json={"user_id": 999, "goal": "Orphan plan", "hours_per_week": 1.0},
    )
    assert response.status_code == 404


def test_update_plan(client, user):
    plan = client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Learn Python", "hours_per_week": 10.0},
    ).json()
    response = client.patch(
        f"/plans/{plan['id']}",
        json={"description": "Updated notes", "target_date": "2026-09-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated notes"
    assert data["target_date"] == "2026-09-01"
    assert data["goal"] == "Learn Python"


def test_update_plan_not_found(client):
    response = client.patch("/plans/999", json={"description": "x"})
    assert response.status_code == 404
