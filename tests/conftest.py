from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.settings import get_app_settings
from db import Base
from db.session import get_database_session, get_engine
from models.order import Order, Status
from models.user import User


@pytest.fixture
def set_environment():
    import os  # noqa: PLC0415

    os.environ["ENVIRONMENT"] = "testing"


@pytest.fixture
def create_tables(set_environment):  # noqa: ARG001
    settings = get_app_settings()
    engine = get_engine(settings)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@pytest.fixture
def test_client(set_environment):
    from main import app

    client = TestClient(app)

    return client


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
