from unittest.mock import MagicMock, patch

from sqlalchemy.exc import IntegrityError


def test_create_user(test_client, create_tables):
    response = test_client.post("/create_user", json={"name": "test_user"})
    assert response.status_code == 201, response.json()


def test_create_user_raises_integrity_error(test_client):
    mock_session = MagicMock()
    mock_session.add.side_effect = IntegrityError(
        statement=None,
        params=None,
        orig=Exception("Deuplicate key"),
    )

    with patch("main.get_database_session", return_value=mock_session):
        response = test_client.post("/create_user", json={"name": "test_user_1"})
        assert response.status_code == 409
