from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_redis_url() -> RedisDsn:
    return RedisDsn("redis://localhost:6379/0")


class RedisSettings(BaseModel):
    url: RedisDsn = Field(
        default_factory=_default_redis_url,
        description="Connection string for the Redis instance used as the event bus.",
    )
    channel_prefix: str = Field(
        default="kali",
        description="Prefix applied to Redis Pub/Sub channels for namespacing.",
    )
    request_channel: str = Field(
        default="agent.requests",
        description="Channel used for inbound orchestration requests.",
    )
    status_channel: str = Field(
        default="agent.status",
        description="Channel used for publishing orchestration status updates.",
    )
    max_connections: int = Field(default=20, ge=1, le=200)

    @property
    def namespaced_request_channel(self) -> str:
        return f"{self.channel_prefix}:{self.request_channel}".lower()

    @property
    def namespaced_status_channel(self) -> str:
        return f"{self.channel_prefix}:{self.status_channel}".lower()


class LangGraphSettings(BaseModel):
    checkpoint_store: Literal["memory", "sqlite"] = Field(default="memory")
    checkpoint_path: str = Field(
        default=".langgraph/checkpoints.sqlite",
        description="Path used when checkpoint_store is set to 'sqlite'.",
    )
    max_concurrency: int = Field(default=32, ge=1, le=256)


_ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE_PATH), env_file_encoding="utf-8")

    environment: Literal["development", "production", "test"] = Field(
        default="development",
        description="Active runtime environment. Influences default Redis selection.",
        validation_alias=AliasChoices("AI_ENV", "environment"),
    )
    redis: RedisSettings = Field(default_factory=RedisSettings)
    redis_url_override: Optional[RedisDsn] = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    langgraph: LangGraphSettings = Field(default_factory=LangGraphSettings)

    @model_validator(mode="after")
    def _configure_redis(cls, settings: "Settings") -> "Settings":
        if settings.environment == "production":
            candidate = settings.redis_url_override or settings.redis.url
            settings.redis = settings.redis.model_copy(update={"url": candidate})
        else:
            settings.redis = settings.redis.model_copy(update={"url": _default_redis_url()})
        return settings

    @property
    def redis_url(self) -> RedisDsn:
        return self.redis.url


def get_settings(override: Optional[dict] = None) -> Settings:
    return Settings(**(override or {}))
