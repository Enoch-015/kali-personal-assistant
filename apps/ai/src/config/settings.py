from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import BaseModel, Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseModel):
    url: RedisDsn = Field(
        default_factory=lambda: RedisDsn("redis://localhost:6379/0"),
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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: Literal["development", "production", "test"] = Field(
        default="development",
        description="Active runtime environment. Influences default Redis selection.",
    )
    redis: RedisSettings = Field(default_factory=RedisSettings)
    langgraph: LangGraphSettings = Field(default_factory=LangGraphSettings)

    @property
    def redis_url(self) -> RedisDsn:
        return self.redis.url


@lru_cache(maxsize=1)
def get_settings(override: Optional[dict] = None) -> Settings:
    if override is None:
        return Settings()
    return Settings(**override)
