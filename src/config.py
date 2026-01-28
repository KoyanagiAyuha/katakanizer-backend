import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# プロジェクトルートの .env ファイルへの絶対パス
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./katakanizer.db", alias="DATABASE_URL")
    db_pool_size: int = Field(default=2, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=3, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=300, alias="DB_POOL_RECYCLE")

    # Firebase
    firebase_project_id: str = Field(default="", alias="FIREBASE_PROJECT_ID")

    # OpenAI
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # Rate Limiting
    free_user_daily_limit: int = Field(default=5, alias="FREE_USER_DAILY_LIMIT")

    # App
    debug: bool = Field(default=False, alias="DEBUG")

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return ["http://localhost:3000"]
        if self.cors_origins.startswith("[") and self.cors_origins.endswith("]"):
            try:
                return json.loads(self.cors_origins)
            except (json.JSONDecodeError, TypeError):
                pass
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    @property
    def is_postgresql(self) -> bool:
        return bool(self.database_url) and not self.database_url.startswith("sqlite")

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
