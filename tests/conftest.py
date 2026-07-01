import logging
import os
from collections.abc import Generator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import Connection, connect
from pytest import MonkeyPatch
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

from alembic import command, script
from core.settings import Settings, get_app_settings
from db import Base
from db.session import get_database_session, get_engine
from models.order import Order, Status
from models.user import User
from tests.helpers import build_postgres_dsn

logger = logging.getLogger(__name__)


@pytest.fixture
def set_environment():
    os.environ["ENVIRONMENT"] = "testing"


@pytest.fixture
def create_tables(set_environment):  # noqa: ARG001
    settings = get_app_settings()
    engine = get_engine(settings)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


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
def user_factory(test_session):
    def create_user(**kwargs):
        user = User(name=kwargs.get("name", "test_user"))
        test_session.add(user)
        test_session.commit()
        return user

    return create_user


@pytest.fixture
def order_factory(test_session):
    def create_order(**kwargs):
        order = Order(
            customer_id=kwargs.get("customer_id"),
            amount=kwargs.get("amount", 1000),
            status=kwargs.get("status", Status.PENDING),
        )
        test_session.add(order)
        test_session.commit()
        return order

    return create_order


@pytest.fixture(scope="session")
def postgres() -> Generator[Connection]:
    postgresql = PostgresContainer("postgres:17", dbname="test_db")
    postgresql.start()

    def load_database_from_alembic(db_connection: Connection):
        dsn = build_postgres_dsn(
            password=postgresql.password, **db_connection.info.get_parameters()
        )
        with db_connection.cursor():
            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", "alembic")

            directory = script.ScriptDirectory.from_config(alembic_cfg)
            logger.debug("current head is %r", directory.get_heads())

            # overwrite existing sqlalchemyURL with test container postgres
            alembic_cfg.set_main_option("sqlalchemy.url", dsn)
            # Given we start with an empty database we start at base.
            # Stamping this sets up the internal Alembic table that is used for
            # versioning in migrations.
            logger.debug("Stamping as current version.")
            command.stamp(alembic_cfg, "base")

            # Upgrade to head
            command.upgrade(alembic_cfg, "head")

            db_connection.commit()

    db_connection = connect(
        dbname=postgresql.dbname,
        user=postgresql.username,
        password=postgresql.password,
        host=postgresql.get_container_host_ip(),
        port=postgresql.get_exposed_port(5432),
    )
    load_database_from_alembic(db_connection)
    return db_connection


@pytest.fixture(scope="session")
def rabbitmq_container():
    with RabbitMqContainer("rabbitmq:4-management") as rabbitmq:
        yield rabbitmq


@pytest.fixture
def test_settings(postgres, rabbitmq_container):
    settings = Settings(
        DB_HOST=postgres.postgresget_container_host_ip(),
        DB_PORT=postgres.postgresget_exposed_port(5432),
        RMQ_HOST=rabbitmq_container.get_container_host_ip(),
        RMQ_PORT=rabbitmq_container.get_exposed_port(5672),
    )
    return settings


@pytest.fixture(scope="session")
def _db(postgres: Connection) -> Generator[Engine]:
    """
    Internal fixture used within the `conftest.py`.
    DO NOT USE THIS FIXTURE IN THE TESTS.
    """

    dsn = build_postgres_dsn(
        host="127.0.0.1",
        port=str(postgres.info.port),
        user=postgres.info.user,
        password=postgres.info.password,
        dbname=postgres.info.dbname,
    )
    engine = create_engine(
        dsn,
        future=True,
        pool_size=80,
        max_overflow=0,
        pool_recycle=10,
        pool_timeout=5,
    )
    yield engine

    engine.dispose()


@pytest.fixture(scope="session")
def test_session(_db):
    gen = get_database_session(_db)
    session = next(gen)
    try:
        yield session
    finally:
        gen.close()


@pytest.fixture(scope="session")
def dev_setting_override(postgres, rabbitmq_container):
    """Override config to use test runner defined over local env."""
    return Settings(
        ENVIRONMENT="testing",
        DB_NAME=postgres.info.dbname,
        DB_PORT=str(postgres.info.port),
        DB_USER=postgres.info.user,
        DB_HOST="localhost",
        RMQ_HOST=rabbitmq_container.get_container_host_ip(),
        RMQ_PORT=int(rabbitmq_container.get_exposed_port(5672)),
        RMQ_USER="guest",
        RMQ_PASSWORD="guest",
    )


@pytest.fixture
def test_client(
    dev_setting_override,
    _db: Engine,
    monkeypatch,
):
    from main import app

    # client = TestClient(app)
    # client.app.dependency_overrides[get_app_settings] = lambda: dev_setting_override
    # client.app.dependency_overrides[get_engine] = lambda: _db

    # return client
    os.environ["ENVIRONMENT"] = "testing"
    app.dependency_overrides[get_app_settings] = lambda: dev_setting_override

    app.dependency_overrides[get_engine] = lambda: _db

    monkeypatch.setattr("main.get_app_settings", lambda: dev_setting_override)
    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
