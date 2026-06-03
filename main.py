import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import models
from core.settings import get_app_settings
from db.base import Base
from db.session import get_database_session, get_engine
from models.user import User
from schemas.user import CreateUser, ReadUser

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_app_settings()
    Base.metadata.create_all(get_engine(settings))
    yield


app = FastAPI(
    title="Order Processing API",
    description="Async order processing service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/create_user", response_model=ReadUser)
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
        raise HTTPException(status_code=409, detail="User already exists") from e
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("Database error")
        raise HTTPException(status_code=500, detail="Internal server error") from e

    return user_obj
