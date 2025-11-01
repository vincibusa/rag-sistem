from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    project_name: str = Field(default="Medit RAG Backend", alias="PROJECT_NAME")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api", alias="API_V1_PREFIX")
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000"], alias="BACKEND_CORS_ORIGINS"
    )

    api_key_header_name: str = Field(default="X-API-Key", alias="API_KEY_HEADER_NAME")
    api_key: str | None = Field(default=None, alias="API_KEY")

    postgres_user: str = Field(default="rag_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="rag_password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="rag_db", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_host_external: str | None = Field(default=None, alias="POSTGRES_HOST_EXTERNAL")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    sqlalchemy_pool_size: int = Field(default=10, alias="SQLALCHEMY_POOL_SIZE")
    sqlalchemy_max_overflow: int = Field(default=10, alias="SQLALCHEMY_MAX_OVERFLOW")

    max_upload_size_mb: int = Field(default=25, alias="MAX_UPLOAD_SIZE_MB")
    allowed_file_extensions: List[str] = Field(
        default_factory=lambda: ["pdf", "doc", "docx", "xls", "xlsx", "txt"],
        alias="ALLOWED_FILE_EXTENSIONS",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @model_validator(mode="before")
    def _split_comma_values(cls, values: dict) -> dict:
        cors_origins = values.get("BACKEND_CORS_ORIGINS")
        if isinstance(cors_origins, str):
            values["BACKEND_CORS_ORIGINS"] = [
                origin.strip() for origin in cors_origins.split(",") if origin.strip()
            ]

        extensions = values.get("ALLOWED_FILE_EXTENSIONS")
        if isinstance(extensions, str):
            values["ALLOWED_FILE_EXTENSIONS"] = [
                ext.strip().lower() for ext in extensions.split(",") if ext.strip()
            ]
        return values

    @property
    def _resolve_postgres_host(self, prefer_external: bool = False) -> str:
        if prefer_external and self.postgres_host_external:
            return self.postgres_host_external

        if self.environment.lower() == "local" and self.postgres_host_external:
            return self.postgres_host_external

        return self.postgres_host

    @property
    def sqlalchemy_database_uri(self) -> str:
        host = self._resolve_postgres_host()
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sqlalchemy_external_uri(self) -> str:
        host = self._resolve_postgres_host(prefer_external=True)
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
