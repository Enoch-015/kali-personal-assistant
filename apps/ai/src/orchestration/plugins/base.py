from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional

from src.orchestration.models import OrchestrationRequest, PluginDispatchResult


class BasePlugin(ABC):
    """Abstract base class for orchestrator plugins.

    Plugins may wrap first-party connectors (WhatsApp, email) or remote MCP servers.
    They receive the structured request along with a rendered payload and should
    return a :class:`PluginDispatchResult` describing what happened.
    """

    name: str
    description: str = ""

    @abstractmethod
    async def dispatch(
        self,
        request: OrchestrationRequest,
        message_body: str,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> PluginDispatchResult:
        """Execute the plugin call for the provided request."""

    def describe(self) -> str:
        if self.description:
            return self.description
        doc = inspect.getdoc(self.__class__)
        return doc or self.name


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

    def names(self) -> list[str]:
        return sorted({key for key in self._plugins.keys()})

    def describe(self) -> Dict[str, str]:
        descriptions: Dict[str, str] = {}
        alias_map: Dict[str, set[str]] = {}
        for key, plugin in self._plugins.items():
            canonical = plugin.name.lower()
            alias_map.setdefault(canonical, set()).add(key)

        for canonical, aliases in alias_map.items():
            plugin = self._plugins.get(canonical)
            if plugin is None:
                continue
            description = plugin.describe()
            alias_list = sorted(alias for alias in aliases if alias != canonical)
            if alias_list:
                description = f"{description} (aliases: {', '.join(alias_list)})"
            descriptions[canonical] = description
        return descriptions


registry = PluginRegistry()
