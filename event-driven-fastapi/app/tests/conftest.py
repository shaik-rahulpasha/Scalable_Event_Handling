import pytest

from fastapi.testclient import TestClient

from app.main import create_application
from app.core.database import (
    create_db_and_tables, drop_db_and_tables, get_session)


@pytest.fixture(scope="module")
def client():
    """Fixture to provide a test client with database setup and teardown."""
    app = create_application()
    with TestClient(app) as client:
        create_db_and_tables()
        yield client
        drop_db_and_tables()


@pytest.fixture(scope="function")
def db_session():
    """Fixture to provide a database session for each test."""
    db = next(get_session())
    yield db
    db.close()
