from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from src.orchestration.models import OrchestrationRequest, PluginDispatchResult
from src.orchestration.plugins.base import BasePlugin, registry

logger = logging.getLogger(__name__)


class DemoMessagingPlugin(BasePlugin):
    """Demo plugin that simulates outbound messaging.

    This acts as a drop-in placeholder until real channel integrations (e.g., WhatsApp)
    are wired in. The plugin sleeps briefly to mimic network latency and stores
    metadata about the "dispatch" operation.
    """

    name = "demo-messaging"

    async def dispatch(
        self,
        request: OrchestrationRequest,
        message_body: str,
        *,
        context: Dict[str, Any] | None = None,
    ) -> PluginDispatchResult:
        await asyncio.sleep(0.05)  # simulate async work
        audience = request.audience.recipients if request.audience else [request.payload.get("recipient", "demo")]
        recipients: List[str] = audience or ["demo@local"]
        logger.info(
            "DemoMessagingPlugin dispatched message to %d recipients for intent %s",
            len(recipients),
            request.intent,
        )
        metadata: Dict[str, Any] = {
            "preview": message_body[:120],
            "intent": request.intent,
        }
        if context:
            metadata["tool_context"] = context
        return PluginDispatchResult(
            plugin_name=self.name,
            dispatched_count=len(recipients),
            failed=[],
            metadata=metadata,
        )


def register_demo_plugin() -> None:
    plugin = DemoMessagingPlugin()
    registry.register(plugin)
    # Provide convenient aliases so demo plugin can respond to common channels.
    registry.register_alias("whatsapp", plugin)
    registry.register_alias("demo", plugin)
