from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str | None
    DB_PORT: str = "5432"
    DB_HOST: str
    DB_NAME: str
    ENVIRONMENT: Literal["local", "testing", "dev", "tst", "uat", "prd"]
    POOL_SIZE: int = 5
    SQLITE_DB_URL: str = "sqlite:///order_processing.db"


def get_app_settings() -> Settings:
    return Settings()
