"""Redis configuration settings."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, RedisDsn


def _default_redis_url() -> RedisDsn:
    return RedisDsn("redis://localhost:6379/0")


class RedisSettings(BaseModel):
    """Redis connection and pub/sub configuration."""

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

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "RedisSettings":
        """Build from Vault ``databases`` secrets."""
        url = secrets.get("redis-url", "redis://localhost:6379/0")
        return cls(
            url=RedisDsn(url),
            channel_prefix=secrets.get("redis-channel-prefix", "kali"),
            request_channel=secrets.get("redis-request-channel", "agent.requests"),
            status_channel=secrets.get("redis-status-channel", "agent.status"),
            max_connections=int(secrets.get("redis-max-connections", 20)),
        )
