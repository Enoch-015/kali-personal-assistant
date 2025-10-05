from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

from redis.asyncio import Redis

from src.config.settings import RedisSettings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RedisEvent:
    channel: str
    payload: Dict[str, Any]


class RedisEventBus:
    """Thin asynchronous wrapper around Redis Pub/Sub used as the agent event bus."""

    def __init__(self, settings: RedisSettings):
        self._settings = settings
        self._redis = Redis.from_url(
            str(settings.url),
            decode_responses=True,
            max_connections=settings.max_connections,
        )
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, payload: Dict[str, Any]) -> None:
        message = json.dumps(payload)
        await self._redis.publish(channel, message)
        logger.debug("Published event to %s: %s", channel, message)

    async def listen(self, channel: str) -> AsyncIterator[RedisEvent]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        logger.info("Subscribed to Redis channel %s", channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.exception("Invalid JSON payload received on %s", channel)
                    continue
                yield RedisEvent(channel=channel, payload=data)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            logger.info("Unsubscribed from Redis channel %s", channel)

    async def ping(self) -> bool:
        try:
            await self._redis.ping()
            return True
        except Exception:  # pragma: no cover - simply signal unreachable redis
            logger.exception("Redis ping failed")
            return False

    async def close(self) -> None:
        await self._redis.close()

    @property
    def request_channel(self) -> str:
        return self._settings.namespaced_request_channel

    @property
    def status_channel(self) -> str:
        return self._settings.namespaced_status_channel
