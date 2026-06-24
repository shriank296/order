import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from exceptions import DatabaseException, InvalidMessage, OrderNotFound
from models.order import Order, Status

logger = logging.getLogger(__name__)


def process_order(payload: dict, session: Session):
    try:
        order_id = UUID(payload["order_id"])
    except (TypeError, ValueError) as e:
        raise InvalidMessage("Invalid order_id") from e
    try:
        order: Order = session.get(Order, order_id)
        if order is None:
            raise OrderNotFound(order_id)
        if order.status == Status.PROCESSED:
            return
        order.status = Status.PROCESSED
        session.commit()
        logger.info("Order processed successfully")
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("A database error occured.")
        raise DatabaseException("Database failure") from e
