import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.order import Order, Status

logger = logging.getLogger(__name__)


def process_order(payload: dict, session: Session):
    try:
        order_id = UUID(payload["order_id"])
        order: Order = session.get(Order, order_id)
        if order is None:
            raise ValueError(f"order {order_id} not found")
        if order.status == Status.PROCESSED:
            return
        order.status = Status.PROCESSED
        session.commit()
        logger.info("Order processed successfully")
    except SQLAlchemyError:
        session.rollback()
        logger.exception("A database error occured.")
        raise
