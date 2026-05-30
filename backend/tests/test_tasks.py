import pytest


@pytest.fixture
def plan(client):
    user = client.post("/users", json={"name": "Alice"}).json()
    return client.post(
        "/plans",
        json={"user_id": user["id"], "goal": "Learn Python", "hours_per_week": 10.0},
    ).json()


def test_create_task(client, plan):
    response = client.post(
        f"/plans/{plan['id']}/tasks",
        json={"title": "Read chapter 1", "estimated_hours": 2.0},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Read chapter 1"
    assert data["estimated_hours"] == 2.0
    assert data["plan_id"] == plan["id"]
    assert isinstance(data["id"], int)


def test_create_task_has_completed_false(client, plan):
    response = client.post(
        f"/plans/{plan['id']}/tasks",
        json={"title": "New task", "estimated_hours": 1.0},
    )
    assert response.status_code == 201
    assert response.json()["completed"] is False


def test_get_tasks(client, plan):
    client.post(
        f"/plans/{plan['id']}/tasks", json={"title": "Task A", "estimated_hours": 1.0}
    )
    client.post(
        f"/plans/{plan['id']}/tasks", json={"title": "Task B", "estimated_hours": 3.0}
    )
    response = client.get(f"/plans/{plan['id']}/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert {t["title"] for t in tasks} == {"Task A", "Task B"}


def test_get_tasks_empty(client, plan):
    response = client.get(f"/plans/{plan['id']}/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_create_task_plan_not_found(client):
    response = client.post(
        "/plans/999/tasks",
        json={"title": "Orphan task", "estimated_hours": 1.0},
    )
    assert response.status_code == 404


def test_toggle_task_complete(client, plan):
    task = client.post(
        f"/plans/{plan['id']}/tasks",
        json={"title": "Read chapter 1", "estimated_hours": 2.0},
    ).json()
    assert task["completed"] is False

    response = client.patch(
        f"/plans/{plan['id']}/tasks/{task['id']}",
        json={"completed": True},
    )
    assert response.status_code == 200
    assert response.json()["completed"] is True


def test_toggle_task_back_to_incomplete(client, plan):
    task = client.post(
        f"/plans/{plan['id']}/tasks",
        json={"title": "Read chapter 1", "estimated_hours": 2.0},
    ).json()
    client.patch(f"/plans/{plan['id']}/tasks/{task['id']}", json={"completed": True})
    response = client.patch(
        f"/plans/{plan['id']}/tasks/{task['id']}", json={"completed": False}
    )
    assert response.status_code == 200
    assert response.json()["completed"] is False


def test_toggle_task_not_found(client, plan):
    response = client.patch(f"/plans/{plan['id']}/tasks/999", json={"completed": True})
    assert response.status_code == 404
