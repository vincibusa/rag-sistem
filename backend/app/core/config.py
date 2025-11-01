from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BASE_DIR / ".env"),
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

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_host_external: str | None = Field(default=None, alias="REDIS_HOST_EXTERNAL")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_host_external: str | None = Field(default=None, alias="QDRANT_HOST_EXTERNAL")
    qdrant_http_port: int = Field(default=6333, alias="QDRANT_HTTP_PORT")
    qdrant_grpc_port: int = Field(default=6334, alias="QDRANT_GRPC_PORT")
    qdrant_collection_name: str = Field(
        default="rag_documents", alias="QDRANT_COLLECTION_NAME"
    )

    ollama_host: str = Field(default="localhost", alias="OLLAMA_HOST")
    ollama_host_external: str | None = Field(default=None, alias="OLLAMA_HOST_EXTERNAL")
    ollama_port: int = Field(default=11434, alias="OLLAMA_PORT")
    ollama_embed_model: str = Field(
        default="mxbai-embed-large", alias="OLLAMA_EMBED_MODEL"
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-5-mini", alias="OPENAI_MODEL_NAME")

    rag_chunk_size: int = Field(default=1000, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=100, alias="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    rag_embedding_dimensions: int = Field(default=1024, alias="RAG_EMBED_DIMENSIONS")
    rag_embedding_name: str = Field(default="default", alias="RAG_EMBED_NAME")

    celery_queue_name: str = Field(
        default="documents", alias="CELERY_QUEUE_NAME"
    )

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

    def _resolve_host(
        self,
        host: str,
        external: str | None,
        *,
        prefer_external: bool = False,
    ) -> str:
        if prefer_external and external:
            return external

        if self.environment.lower() == "local" and external:
            return external

        return host

    @property
    def sqlalchemy_database_uri(self) -> str:
        host = self._resolve_host(self.postgres_host, self.postgres_host_external)
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sqlalchemy_external_uri(self) -> str:
        host = self._resolve_host(
            self.postgres_host,
            self.postgres_host_external,
            prefer_external=True,
        )
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def redis_host_resolved(self) -> str:
        return self._resolve_host(self.redis_host, self.redis_host_external)

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host_resolved}:{self.redis_port}/0"

    @property
    def redis_external_url(self) -> str:
        host = self._resolve_host(
            self.redis_host,
            self.redis_host_external,
            prefer_external=True,
        )
        return f"redis://{host}:{self.redis_port}/0"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    @property
    def qdrant_host_resolved(self) -> str:
        return self._resolve_host(self.qdrant_host, self.qdrant_host_external)

    @property
    def qdrant_http_url(self) -> str:
        return f"http://{self.qdrant_host_resolved}:{self.qdrant_http_port}"

    @property
    def qdrant_external_http_url(self) -> str:
        host = self._resolve_host(
            self.qdrant_host,
            self.qdrant_host_external,
            prefer_external=True,
        )
        return f"http://{host}:{self.qdrant_http_port}"

    @property
    def qdrant_client_kwargs(self) -> dict[str, Any]:
        return {
            "host": self.qdrant_host_resolved,
            "port": self.qdrant_http_port,
        }

    @property
    def ollama_host_resolved(self) -> str:
        return self._resolve_host(self.ollama_host, self.ollama_host_external)

    @property
    def ollama_base_url(self) -> str:
        return f"http://{self.ollama_host_resolved}:{self.ollama_port}/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
