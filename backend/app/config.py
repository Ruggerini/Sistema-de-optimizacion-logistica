from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "St. Joseph Recycling Route Optimizer"
    secret_key: str = "change-this-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    database_url: str = "sqlite:///./data/optimizer.db"
    mapbox_token: str
    allowed_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
