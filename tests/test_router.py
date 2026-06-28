from unittest.mock import MagicMock
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from brokers.rabbitmq import get_message_broker
from db.session import get_database_session
from main import app
from models import User
from models.order import Order


def test_create_user(postgres, test_client):  # noqa: ARG001
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


def test_create_order(test_client, postgres, test_session):  # noqa: ARG001
    """
    Tests order create endpoint.

    Creates User object and uses it to create a order.
    Overrides get broker depedency to use mock broker.
    """
    user = User(name="test_user2")
    test_session.add(user)
    test_session.commit()
    mock_broker = MagicMock()
    app.dependency_overrides[get_message_broker] = lambda: mock_broker
    try:
        response = test_client.post(
            "/place_order",
            json={"customer_name": "test_user2", "amount": 1000, "status": "pending"},
        )
        assert response.status_code == 201, response.json()  # noqa: PLR2004
        order = test_session.get(Order, UUID(response.json()["id"]))
        assert order is not None  # noqa: S101
        assert order.customer_id == user.id  # noqa: S101
        mock_broker.publish.assert_called_once_with(
            exchange="order_exchange",
            routing_key="order.created",
            body={"order_id": str(response.json()["id"])},
        )
    finally:
        app.dependency_overrides.clear()


def test_get_order_sucessfull(
    test_client, postgres, test_session, order_factory, user_factory
):  # noqa: ARG001
    user = user_factory(name="random_user")
    order = order_factory(customer_id=user.id, amount=2000)
    order_id = order.id
    response = test_client.get(f"/order/{order_id}")
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["id"] == str(order.id)
    assert data["customerId"] == str(user.id)
    assert data["amount"] == 2000
    assert data["status"] == "pending"


def test_get_order_not_found(test_client, postgres, test_session):
    response = test_client.get("/order/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404, response.json()
    assert (
        response.json()["detail"]
        == "Order with id 00000000-0000-0000-0000-000000000000 not found"
    )


def test_create_order_customer_not_found(test_client, postgres, test_session):
    response = test_client.post(
        "/place_order",
        json={"customer_name": "test_user3", "amount": 1000, "status": "pending"},
    )
    assert response.status_code == 404, response.json()
    assert response.json()["detail"] == "Customer test_user3 does not exist"


def test_create_order_validation_error(test_client, postgres, test_session):
    response = test_client.post(
        "/place_order",
        json={"customer_name": "test_user4", "amount": "str", "status": "pending"},
    )
    assert response.status_code == 422, response.json()
