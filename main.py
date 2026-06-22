import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import models  # noqa: F401
from brokers.rabbitmq import RabbitMq, get_message_broker
from core.logging import configure_logging
from core.settings import get_app_settings
from db.base import Base
from db.session import get_database_session, get_engine
from models.order import Order
from models.user import User
from schemas.order import CreateOrder, ReadOrder
from schemas.user import CreateUser, ReadUser

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    settings = get_app_settings()
    Base.metadata.create_all(get_engine(settings))
    broker = get_message_broker(settings)
    broker.connect()
    yield
    broker.close()


configure_logging()

app = FastAPI(
    title="Order Processing API",
    description="Async order processing service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/create_user", response_model=ReadUser, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: CreateUser,
    session: Annotated[Session, Depends(get_database_session)],
):
    user_obj = User(**user_in.model_dump())
    try:
        session.add(user_obj)
        session.commit()
    except IntegrityError as e:
        session.rollback()
        logger.exception("User already exists", extra={"user": user_in.name})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        ) from e
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("Database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e

    return user_obj


@app.post("/place_order", response_model=ReadOrder, status_code=status.HTTP_201_CREATED)
def place_order(
    order_in: CreateOrder,
    session: Annotated[Session, Depends(get_database_session)],
    broker: Annotated[RabbitMq, Depends(get_message_broker)],
):
    stmt = select(User).where(User.name == order_in.customer_name)
    customer = session.scalars(stmt).one_or_none()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {order_in.customer_name} does not exist",
        )

    order_dict = order_in.model_dump(exclude="customer_name")
    order_dict["customer_id"] = customer.id
    order_obj = Order(**order_dict)
    try:
        session.add(order_obj)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("Database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e

    broker.publish(
        exchange="order_exchange",
        routing_key="order.created",
        body={"order_id": str(order_obj.id)},
    )
    logger.info("Message sent successfully!")

    return order_obj


@app.get("/order/{order_id}", response_model=ReadOrder)
def get_order(
    order_id: UUID,
    session: Annotated[Session, Depends(get_database_session)],
):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found",
        )
    return order
