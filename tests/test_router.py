import json


def test_create_user(test_client, create_tables):
    response = test_client.post("/create_user", json={"name": "test_user"})
    assert response.status_code == 201, response.json()
