import asyncio
import time
import uuid

import pytest

from src.services.redis_client import (
    close_async_redis,
    delete_ephemeral,
    fetch_ephemeral,
    get_async_redis,
    store_ephemeral,
    touch_ephemeral,
)


@pytest.mark.asyncio
async def test_get_async_redis_connection(monkeypatch) -> None:
    client = await get_async_redis()
    if client is None:
        pytest.skip("Redis server not available for redis_client tests")
    await close_async_redis()


@pytest.mark.asyncio
async def test_ephemeral_token_lifecycle(monkeypatch) -> None:
    client = await get_async_redis()
    if client is None:
        pytest.skip("Redis server not available for redis_client tests")

    token = uuid.uuid4().hex
    exp = int(time.time()) + 5

    await delete_ephemeral(token)
    await store_ephemeral(token, user_id=123, exp=exp)

    data = await fetch_ephemeral(token)
    assert data is not None
    assert data["user_id"] == 123

    await touch_ephemeral(token)
    await delete_ephemeral(token)

    data_after_delete = await fetch_ephemeral(token)
    assert data_after_delete is None

    await close_async_redis()
