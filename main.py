from contextlib import asynccontextmanager

from fastapi import FastAPI

import models
from core.settings import get_app_settings
from db.base import Base
from db.session import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_app_settings()
    print(Base.metadata.tables.keys())
    breakpoint()
    Base.metadata.create_all(get_engine(settings))
    yield


app = FastAPI(
    title="Order Processing API",
    description="Async order processing service",
    version="1.0.0",
    lifespan=lifespan,
)
