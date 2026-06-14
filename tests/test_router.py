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
from models.order import Order, Status


def test_create_user(test_client, create_tables):  # noqa: ARG001
    response = test_client.post("/create_user", json={"name": "test_user"})
    assert response.status_code == 201, response.json()  # noqa: PLR2004


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
        assert response.status_code == 409  # noqa: PLR2004
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
        assert response.status_code == 201, response.json()  # noqa: PLR2004
        order = db_session.get(Order, UUID(response.json()["id"]))
        assert order is not None  # noqa: S101
        assert order.customer_id == user.id  # noqa: S101
        mock_broker.send.assert_called_once_with(
            queue_name="order",
            body={"order_id": str(response.json()["id"])},
        )
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def user_factory(db_session):
    def create_user(**kwargs):
        user = User(name=kwargs.get("name", "test_user"))
        db_session.add(user)
        db_session.commit()
        return user

    return create_user


@pytest.fixture
def order_factory(db_session):
    def create_order(**kwargs):
        order = Order(
            customer_id=kwargs.get("customer_id"),
            amount=kwargs.get("amount", 1000),
            status=kwargs.get("status", Status.PENDING),
        )
        db_session.add(order)
        db_session.commit()
        return order

    return create_order


def test_get_order(test_client, create_tables, db_session, order_factory, user_factory):  # noqa: ARG001
    user = user_factory()
    order = order_factory(customer_id=user.id, amount=2000)
    order_id = order.id
    response = test_client.get(f"/order/{order_id}")
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["id"] == str(order.id)
    assert data["customerId"] == str(user.id)
    assert data["amount"] == 2000
    assert data["status"] == "pending"


def test_get_order_not_found(test_client, create_tables, db_session):
    response = test_client.get("/order/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404, response.json()
    assert (
        response.json()["detail"]
        == "Order with id 00000000-0000-0000-0000-000000000000 not found"
    )


def test_create_order_customer_not_found(test_client, create_tables, db_session):
    response = test_client.post(
        "/place_order",
        json={"customer_name": "test_user2", "amount": 1000, "status": "pending"},
    )
    assert response.status_code == 404, response.json()
    assert response.json()["detail"] == "Customer test_user2 does not exist"


def test_create_order_validation_error(test_client, create_tables, db_session):
    response = test_client.post(
        "/place_order",
        json={"customer_name": "test_user2", "amount": "str", "status": "pending"},
    )
    assert response.status_code == 422, response.json()
