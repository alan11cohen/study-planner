def test_create_user(client):
    response = client.post("/users", json={"name": "Alice"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert isinstance(data["id"], int)


def test_get_user(client):
    created = client.post("/users", json={"name": "Bob"}).json()
    response = client.get(f"/users/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Bob"


def test_get_user_not_found(client):
    response = client.get("/users/999")
    assert response.status_code == 404


def test_list_users(client):
    client.post("/users", json={"name": "Alice"})
    client.post("/users", json={"name": "Bob"})
    response = client.get("/users")
    assert response.status_code == 200
    names = {u["name"] for u in response.json()}
    assert names == {"Alice", "Bob"}


def test_list_users_empty(client):
    response = client.get("/users")
    assert response.status_code == 200
    assert response.json() == []
