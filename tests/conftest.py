import logging
from collections.abc import Generator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import Connection, connect
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


@pytest.fixture(scope="session")
def postres_container() -> Generator[Connection]:
    postgresql = PostgresContainer("postgres:17-alpine", dbname="test_db")
    postgresql.start()

    def load_database_from_alembic(db_connection: Connection):
        dsn = build_postgres_dsn(
            password=postgresql.password, **db_connection.info.dsn_parameters
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
def test_settings(postres_container, rabbitmq_container):
    settings = Settings(
        DB_HOST=postres_container.get_container_host_ip(),
        DB_PORT=postres_container.get_exposed_port(5432),
        RMQ_HOST=rabbitmq_container.get_container_host_ip(),
        RMQ_PORT=rabbitmq_container.get_exposed_port(5672),
    )
    return settings
