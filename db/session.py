import logging
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.settings import Settings, get_app_settings

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)

# SQLITE_DB_URL = "sqlite:///order_processing.db"

_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None


def _get_engine(settings: Settings):
    global _ENGINE

    logger.debug("Setting up new database engine.")

    if settings.ENVIRONMENT not in ("dev", "tst", "uat", "prd"):
        # db_url = f"postresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        db_url = settings.SQLITE_DB_URL
    else:
        pass

    if not _ENGINE:
        _ENGINE = create_engine(
            db_url,
            # Main pool size
            pool_size=settings.POOL_SIZE,
            # Overflow pool that is used if main pool is saturated.
            max_overflow=10,
            # Checkout a new connection with the DB after an connection
            # has been idle for more than 15 minutes.
            pool_recycle=900,
            # timeout time for waiting to create a new connection within
            # the pool. If this is exceeded a Timeout is thrown.
            pool_timeout=5,
            # This is required for the token refresh to fire on every connection.
            pool_pre_ping=True,
            # Use the 2.0 API.
            future=True,
        )
    return _ENGINE


def get_engine(settings: Annotated[Settings, Depends(get_app_settings)]) -> Engine:
    """
    Get the active database session.

    Args: None

    Returns:
        App database engine

    """
    return _get_engine(settings)


def _get_database_session(engine: Engine) -> Generator[Session]:
    global _SESSION_FACTORY

    if not _SESSION_FACTORY:
        _SESSION_FACTORY = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = _SESSION_FACTORY()

    yield session

    session.close()


def get_database_session(
    engine: Annotated[Engine, Depends(get_engine)],
) -> Generator[Session]:
    yield from _get_database_session(engine)
