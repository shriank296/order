from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError

from brokers.rabbitmq import get_message_broker
from core.settings import get_app_settings
from db.session import get_database_session, get_engine
from main import app
from models import User
from models.order import Order


def test_create_user(test_client, create_tables):  # noqa: ARG001
    response = test_client.post("/create_user", json={"name": "test_user"})
    assert response.status_code == 201, response.json()  # noqa: PLR2004, S101


def test_create_user_raises_integrity_error(test_client):
    mock_session = MagicMock()
    mock_session.commit.side_effect = IntegrityError(
        statement=None,
        params=None,
        orig=Exception("Deuplicate key"),
    )

    app.dependency_overrides[get_database_session] = lambda: mock_session
    try:
        response = test_client.post("/create_user", json={"name": "test_user_1"})
        assert response.status_code == 409  # noqa: PLR2004, S101
        mock_session.rollback.asser_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def db_session(set_environment) -> Generator[Session]:  # noqa: ARG001
    settings = get_app_settings()
    engine = get_engine(settings)
    gen = get_database_session(engine)
    session = next(gen)
    try:
        yield session
    finally:
        gen.close()


def test_create_order(test_client, create_tables, set_environment, db_session):  # noqa: ARG001
    """
    Tests order create endpoint.

    Creates User object and uses it to create a order.
    Overrides get broker depedency to use mock broker.
    """
    user = User(name="test_user2")
    db_session.add(user)
    db_session.commit()
    mock_broker = MagicMock()
    app.dependency_overrides[get_message_broker] = lambda: mock_broker
    try:
        response = test_client.post(
            "/place_order",
            json={"customer_name": "test_user2", "amount": 1000, "status": "pending"},
        )
        assert response.status_code == 201, response.json()  # noqa: PLR2004, S101
        order = db_session.get(Order, UUID(response.json()["id"]))
        assert order is not None  # noqa: S101
        assert order.customer_id == user.id  # noqa: S101
        mock_broker.send.assert_called_once_with(
            queue_name="order",
            body={"order_id": str(response.json()["id"])},
        )
    finally:
        app.dependency_overrides.clear()


def test_get_order(test_client, create_tables, db_session):
    user = User(name="test_user3")
    db_session.add(user)
    db_session.flush()
    order = Order(customer_id=user.id, amount=2000, status="pending")
    db_session.add(order)
    db_session.commit()
    order_id = order.id
    response = test_client.get(f"/order/{order_id}")
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["id"] == str(order.id)
    assert data["customerId"] == str(user.id)
    assert data["amount"] == 2000
    assert data["status"] == "pending"
