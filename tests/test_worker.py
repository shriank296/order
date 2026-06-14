from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from models.order import Order, Status
from services.order_processing import process_order


def test_process_order_successful(
    user_factory, order_factory, db_session, create_tables
):
    user = user_factory()
    order = order_factory(customer_id=user.id)
    process_order({"order_id": str(order.id)}, db_session)
    order = db_session.get(Order, order.id)
    assert order.status == Status.PROCESSED


def test_process_order_unsuccessful(db_session, create_tables):
    mock_session = MagicMock()
    mock_order = MagicMock()
    mock_session.get.return_value = mock_order
    mock_session.commit.side_effect = SQLAlchemyError("DB Error")
    with pytest.raises(SQLAlchemyError):
        process_order(
            {"order_id": "00000000-0000-0000-0000-000000000000"}, mock_session
        )
    mock_session.rollback.assert_called_once()
