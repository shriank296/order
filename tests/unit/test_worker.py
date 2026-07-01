from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from exceptions import DatabaseException, InvalidMessage, OrderNotFound
from models.order import Order, Status
from services.order_processing import process_order


def test_process_order_successful(user_factory, order_factory, test_session, postgres):
    user = user_factory(name="test_user5")
    order = order_factory(customer_id=user.id)
    process_order({"order_id": str(order.id)}, test_session)
    order = test_session.get(Order, order.id)
    assert order.status == Status.PROCESSED


def test_process_order_unsuccessful(test_session, postgres):
    mock_session = MagicMock()
    mock_order = MagicMock()
    mock_session.get.return_value = mock_order
    mock_session.commit.side_effect = SQLAlchemyError("DB Error")
    with pytest.raises(DatabaseException):
        process_order(
            {"order_id": "00000000-0000-0000-0000-000000000000"}, mock_session
        )
    mock_session.rollback.assert_called_once()


def test_process_order_invalid_uuid(test_session, postgres):
    with pytest.raises(InvalidMessage):
        process_order({"order_id": "not-a-uuid"}, test_session)


def test_process_order_not_in_db(test_session, postgres):
    mock_session = MagicMock()
    mock_session.get.return_value = None
    with pytest.raises(OrderNotFound):
        process_order(
            process_order(
                {"order_id": "00000000-0000-0000-0000-000000000000"}, mock_session
            )
        )
