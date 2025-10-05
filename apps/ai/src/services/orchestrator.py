from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from langgraph.checkpoint.memory import InMemorySaver

from src.config.settings import Settings
from src.event_bus.redis_bus import RedisEventBus
from src.orchestration.graph import build_langgraph
from src.orchestration.models import (
    AgentEvent,
    AgentState,
    MemoryUpdate,
    OrchestrationRequest,
    PolicyDecision,
    PluginDispatchResult,
    ReviewFeedback,
    WorkflowStatus,
)
from src.orchestration.plugins.demo import register_demo_plugin

logger = logging.getLogger(__name__)


def _serialize_events(events: Optional[list[Any]]) -> Optional[list[Dict[str, Any]]]:
    if not events:
        return events
    serialized: list[Dict[str, Any]] = []
    for event in events:
        if isinstance(event, AgentEvent):
            serialized.append(event.model_dump())
        elif isinstance(event, dict):
            serialized.append(event)
        else:  # pragma: no cover - defensive path
            serialized.append({"type": "unknown", "message": str(event)})
    return serialized


def serialize_state(state: AgentState) -> Dict[str, Any]:
    serialized: Dict[str, Any] = dict(state)
    request = serialized.get("request")
    if isinstance(request, OrchestrationRequest):
        serialized["request"] = request.model_dump()
    status = serialized.get("status")
    if isinstance(status, WorkflowStatus):
        serialized["status"] = status.value
    plugin_result = serialized.get("plugin_result")
    if isinstance(plugin_result, PluginDispatchResult):
        serialized["plugin_result"] = plugin_result.model_dump()
    policy_decision = serialized.get("policy_decision")
    if isinstance(policy_decision, PolicyDecision):
        serialized["policy_decision"] = policy_decision.model_dump()
    review_feedback = serialized.get("review_feedback")
    if isinstance(review_feedback, ReviewFeedback):
        serialized["review_feedback"] = review_feedback.model_dump()
    updates = serialized.get("memory_updates")
    if updates and isinstance(updates, list) and isinstance(updates[0], MemoryUpdate):
        serialized["memory_updates"] = [update.model_dump() for update in updates]
    serialized["events"] = _serialize_events(serialized.get("events"))
    return serialized


class AgentOrchestrator:
    def __init__(
        self,
        settings: Settings,
        event_bus: RedisEventBus,
        checkpointer: Optional[InMemorySaver] = None,
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus
        self._checkpointer = checkpointer or InMemorySaver()
        self._graph = build_langgraph(checkpointer=self._checkpointer)
        self._consumer_task: Optional[asyncio.Task[None]] = None
        self._shutdown = asyncio.Event()
        register_demo_plugin()

    async def start(self) -> None:
        if self._consumer_task is None or self._consumer_task.done():
            self._shutdown.clear()
            self._consumer_task = asyncio.create_task(self._consume_loop())
            logger.info("Agent orchestrator consumer started")

    async def stop(self) -> None:
        if self._consumer_task:
            self._shutdown.set()
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:  # pragma: no cover - normal cancellation path
                pass
            self._consumer_task = None
        logger.info("Agent orchestrator consumer stopped")

    async def enqueue(self, request: OrchestrationRequest) -> str:
        payload = {
            "run_id": request.request_id,
            "request": request.model_dump(),
        }
        await self._event_bus.publish(self._event_bus.request_channel, payload)
        return request.request_id

    async def run(self, request: OrchestrationRequest, run_id: Optional[str] = None) -> AgentState:
        config = {
            "configurable": {
                "thread_id": run_id or request.request_id,
            }
        }
        result: AgentState = await self._graph.ainvoke({"request": request}, config=config)
        return result

    async def get_state(self, run_id: str) -> Optional[AgentState]:
        config = {"configurable": {"thread_id": run_id}}
        snapshot = await self._graph.aget_state(config)
        if snapshot is None:
            return None
        return snapshot.values

    async def _consume_loop(self) -> None:
        try:
            async for event in self._event_bus.listen(self._event_bus.request_channel):
                if self._shutdown.is_set():
                    break
                payload = event.payload
                try:
                    request_data = payload.get("request", payload)
                    request = OrchestrationRequest.model_validate(request_data)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Failed to parse orchestration request: %s", exc)
                    continue

                run_id = payload.get("run_id") or request.request_id
                try:
                    result = await self.run(request, run_id=run_id)
                except Exception as exc:  # pragma: no cover - orchestrator should not crash
                    logger.exception("Orchestration execution failed: %s", exc)
                    status_payload = {
                        "run_id": run_id,
                        "status": WorkflowStatus.FAILED.value,
                        "error": str(exc),
                    }
                    await self._event_bus.publish(self._event_bus.status_channel, status_payload)
                    continue

                serialized = serialize_state(result)
                serialized.update({"run_id": run_id, "status": serialized.get("status")})
                await self._event_bus.publish(self._event_bus.status_channel, serialized)
        finally:
            logger.info("Agent orchestrator consumer loop exited")


async def bootstrap_orchestrator(settings: Settings, event_bus: RedisEventBus) -> AgentOrchestrator:
    orchestrator = AgentOrchestrator(settings=settings, event_bus=event_bus)
    await orchestrator.start()
    return orchestrator
