from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from config.settings import get_settings

_async_redis_singleton: Optional[AsyncRedis] = None
_EPHEMERAL_PREFIX = "ephemeral:v1:"


async def _create_async_client() -> Optional[AsyncRedis]:
    settings = get_settings("ai")
    url = str(settings.redis_url)

    client = AsyncRedis.from_url(
        url,
        decode_responses=True,
        max_connections=settings.redis.max_connections,
    )
    try:
        await client.ping()
    except Exception:  # pragma: no cover - network failure path
        await client.aclose()
        return None
    return client


async def get_async_redis() -> Optional[AsyncRedis]:
    global _async_redis_singleton
    if _async_redis_singleton is not None:
        return _async_redis_singleton
    _async_redis_singleton = await _create_async_client()
    return _async_redis_singleton


async def close_async_redis() -> None:
    global _async_redis_singleton
    if _async_redis_singleton is not None:
        await _async_redis_singleton.aclose()
        _async_redis_singleton = None


async def store_ephemeral(token: str, user_id: int, exp: int) -> None:
    client = await get_async_redis()
    if client is None:
        return
    ttl = max(0, exp - int(time.time()))
    payload: Dict[str, Any] = {"user_id": user_id, "exp": exp, "created": int(time.time())}
    try:
        await client.setex(_EPHEMERAL_PREFIX + token, ttl, json.dumps(payload))
    except RedisError:  # pragma: no cover - network failure path
        pass


async def fetch_ephemeral(token: str) -> Optional[Dict[str, Any]]:
    client = await get_async_redis()
    if client is None:
        return None
    key = _EPHEMERAL_PREFIX + token
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        data: Dict[str, Any] = json.loads(raw)
        if int(data.get("exp", 0)) < int(time.time()):
            await client.delete(key)
            return None
        return data
    except (RedisError, json.JSONDecodeError):  # pragma: no cover - defensive
        return None


async def touch_ephemeral(token: str) -> None:
    client = await get_async_redis()
    if client is None:
        return
    key = _EPHEMERAL_PREFIX + token
    try:
        exists = await client.exists(key)
        if not exists:
            return
        raw = await client.get(key)
        if raw is None:
            return
        data: Dict[str, Any] = json.loads(raw)
        exp = int(data.get("exp", 0))
        ttl = exp - int(time.time())
        if ttl > 0:
            await client.expire(key, ttl)
    except (RedisError, json.JSONDecodeError):  # pragma: no cover - defensive
        return


async def delete_ephemeral(token: str) -> None:
    client = await get_async_redis()
    if client is None:
        return
    try:
        await client.delete(_EPHEMERAL_PREFIX + token)
    except RedisError:  # pragma: no cover - defensive
        return
