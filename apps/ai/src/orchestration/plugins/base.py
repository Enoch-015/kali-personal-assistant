from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable, Optional

from src.orchestration.models import OrchestrationRequest, PluginDispatchResult


class BasePlugin(ABC):
    """Abstract base class for orchestrator plugins.

    Plugins may wrap first-party connectors (WhatsApp, email) or remote MCP servers.
    They receive the structured request along with a rendered payload and should
    return a :class:`PluginDispatchResult` describing what happened.
    """

    name: str

    @abstractmethod
    async def dispatch(
        self,
        request: OrchestrationRequest,
        message_body: str,
    ) -> PluginDispatchResult:
        """Execute the plugin call for the provided request."""


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: Dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin) -> None:
        key = plugin.name.lower()
        self._plugins[key] = plugin

    def register_alias(self, alias: str, plugin: BasePlugin) -> None:
        self._plugins[alias.lower()] = plugin

    def get(self, name: Optional[str]) -> Optional[BasePlugin]:
        if not name:
            return None
        return self._plugins.get(name.lower())

    def all(self) -> Iterable[BasePlugin]:
        return self._plugins.values()


registry = PluginRegistry()
