import asyncio
import contextlib
import uuid

import pytest

from src.config.settings import RedisSettings
from src.event_bus.redis_bus import RedisEventBus


@pytest.mark.asyncio
async def test_redis_event_bus_ping() -> None:
    settings = RedisSettings(channel_prefix=f"test:{uuid.uuid4()}")
    bus = RedisEventBus(settings)
    try:
        if not await bus.ping():
            pytest.skip("Redis server is not reachable; skipping integration test")
    finally:
        await bus.close()


@pytest.mark.asyncio
async def test_redis_event_bus_publish_and_listen() -> None:
    settings = RedisSettings(channel_prefix=f"test:{uuid.uuid4()}")
    bus = RedisEventBus(settings)

    if not await bus.ping():
        await bus.close()
        pytest.skip("Redis server is not reachable; skipping integration test")

    received_event: dict | None = None

    async def subscriber() -> None:
        nonlocal received_event
        async for event in bus.listen(settings.namespaced_request_channel):
            received_event = event.payload
            break

    task = asyncio.create_task(subscriber())
    try:
        payload = {"hello": "world", "request_id": str(uuid.uuid4())}
        await asyncio.sleep(0.05)
        await bus.publish(settings.namespaced_request_channel, payload)
        await asyncio.wait_for(task, timeout=2)
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await bus.close()

    assert received_event == payload
