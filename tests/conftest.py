import pytest
from fastapi.testclient import TestClient

from core.settings import get_app_settings
from db import Base
from db.session import get_engine


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
