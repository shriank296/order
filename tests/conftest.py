import pytest
from fastapi.testclient import TestClient

TEST_DB_URL = "sqlite:///memory:"


@pytest.fixture
def test_client():
    import os

    os.environ["ENVIRONMENT"] = "testing"
    from main import app

    app.dependency_overrides["get_database_session"]

    pass
