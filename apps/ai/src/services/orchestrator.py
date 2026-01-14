from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver

from config.settings import Settings
from src.event_bus.redis_bus import RedisEventBus
from src.orchestration.graph import build_langgraph
from src.orchestration.models import (
    AgentEvent,
    AgentState,
    MemoryUpdate,
    NaturalLanguageGraphRequest,
    OrchestrationRequest,
    PolicyDecision,
    PluginDispatchResult,
    ReviewFeedback,
    WorkflowStatus,
)
from src.orchestration.plugins.demo import register_demo_plugin
from src.orchestration.plugins.resend_email import register_resend_plugin
from src.orchestration.reasoning import configure_reasoning_from_settings

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
        configure_reasoning_from_settings(settings)
        self._graph = build_langgraph(checkpointer=self._checkpointer)
        self._consumer_task: Optional[asyncio.Task[None]] = None
        self._shutdown = asyncio.Event()
        register_resend_plugin()
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

    def _prepare_run_payload(
        self,
        request: Union[OrchestrationRequest, NaturalLanguageGraphRequest],
    ) -> Dict[str, Any]:
        if isinstance(request, OrchestrationRequest):
            return {
                "run_id": request.request_id,
                "kind": "structured",
                "request": request.model_dump(),
            }
        if isinstance(request, NaturalLanguageGraphRequest):
            return {
                "run_id": request.request_id,
                "kind": "natural_language",
                "raw_prompt": request.prompt,
                "request_hints": request.normalized_hints,
            }
        raise TypeError(f"Unsupported request type: {type(request).__name__}")

    async def enqueue(
        self,
        request: Union[OrchestrationRequest, NaturalLanguageGraphRequest],
    ) -> str:
        payload = self._prepare_run_payload(request)
        await self._event_bus.publish(self._event_bus.request_channel, payload)
        return payload["run_id"]

    async def run(
        self,
        request: Union[OrchestrationRequest, NaturalLanguageGraphRequest],
        run_id: Optional[str] = None,
    ) -> AgentState:
        payload = self._prepare_run_payload(request)
        thread_id = run_id or payload["run_id"]
        if payload["kind"] == "structured":
            request_obj = OrchestrationRequest.model_validate(payload["request"])
            state_input: Dict[str, Any] = {"request": request_obj}
        else:
            state_input = {
                "raw_prompt": payload["raw_prompt"],
                "request_hints": payload.get("request_hints") or {},
                "working_notes": [],
                "events": [],
                "status": WorkflowStatus.QUEUED,
                "request_id_hint": thread_id,
            }

        config = {"configurable": {"thread_id": thread_id}}
        result: AgentState = await self._graph.ainvoke(state_input, config=config)
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
                kind = payload.get("kind", "structured")
                run_id = payload.get("run_id")

                if kind == "structured":
                    try:
                        request_data = payload.get("request", payload)
                        request = OrchestrationRequest.model_validate(request_data)
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.exception("Failed to parse orchestration request: %s", exc)
                        continue
                    run_id = run_id or request.request_id
                    request_input: Union[OrchestrationRequest, NaturalLanguageGraphRequest] = request
                elif kind == "natural_language":
                    raw_prompt = payload.get("raw_prompt")
                    if not raw_prompt:
                        logger.warning("Received natural language payload without prompt; skipping")
                        continue
                    effective_id = run_id or payload.get("request_id") or str(uuid4())
                    try:
                        request_input = NaturalLanguageGraphRequest.model_validate(
                            {
                                "request_id": effective_id,
                                "prompt": raw_prompt,
                                "hints": payload.get("request_hints"),
                            }
                        )
                    except Exception as exc:
                        logger.exception("Failed to parse natural language request: %s", exc)
                        continue
                    run_id = request_input.request_id
                else:
                    logger.warning("Unknown payload kind '%s'", kind)
                    continue

                try:
                    result = await self.run(request_input, run_id=run_id)
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
