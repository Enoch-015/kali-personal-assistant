from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional, Protocol

from src.services.graphiti_client import GraphitiClient, get_graphiti_client

from .models import MemorySnapshot, MemoryUpdate, OrchestrationRequest, PluginDispatchResult


class GraphitiClientProtocol(Protocol):
    enabled: bool
    default_group_id: Optional[str] 
    async def search_facts(
        self,
        query: str,
        *,
        center_node_uuid: Optional[str] = None,
        group_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]: ... 

    async def search_nodes(
        self,
        query: str,
        *,
        group_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]: ...

    async def record_memory_update(
        self,
        *,
        summary: str,
        annotations: Dict[str, Any],
        request_payload: Dict[str, Any],
        group_id: Optional[str] = None,
    ) -> None: ...


class MemoryService:
    """Memory provider backed by Graphiti when available."""

    def __init__(self, graphiti_client: Optional[GraphitiClientProtocol] = None) -> None:
        self._graphiti: GraphitiClientProtocol = graphiti_client or get_graphiti_client()
        self._logger = logging.getLogger(__name__)

    @property
    def provider(self) -> str:
        return "graphiti" if self._graphiti.enabled else "placeholder"

    async def retrieve_context(self, request: OrchestrationRequest) -> MemorySnapshot:
        query = request.metadata.get("graphiti_query") if request.metadata else None
        query = query or request.intent
        group_id = self._derive_group_id(request)

        memory_snippets: List[str] = []
        graph_relations: List[str] = []

        if self._graphiti.enabled:  
            center_uuid = None
            if request.metadata:
                center_uuid = request.metadata.get("graphiti_center_node")
            memory_snippets = await self._graphiti.search_facts(
                query,
                center_node_uuid=center_uuid,
                group_id=group_id,
            )
            graph_relations = await self._graphiti.search_nodes(
                query,
                group_id=group_id,
            )

        if not memory_snippets:
            prefix = "graphiti" if self._graphiti.enabled else "demo"
            memory_snippets = [
                f"[{prefix}] No prior episodes matched query '{query}'.",
                f"[{prefix}] Last intent observed: {request.intent}",
            ]

        if not graph_relations:
            graph_relations = [
                "[graphiti] No related entities yet." if self._graphiti.enabled else "[demo] No graph data."
            ]

        vector_results: List[str] = []
        freshness = 60 if self._graphiti.enabled else 5

        return MemorySnapshot(
            memory_snippets=memory_snippets,
            graph_relations=graph_relations,
            vector_results=vector_results,
            freshness_seconds=freshness,
        )

    def validate_relevance(self, snapshot: MemorySnapshot, intent: str) -> Dict[str, str]:
        relevant = any(intent.lower() in snippet.lower() for snippet in snapshot.memory_snippets)
        return {
            "relevant": "true" if relevant else "false",
            "summary": "Relevant snippets present" if relevant else "No matched snippets",
        }

    def prepare_updates(
        self,
        request: OrchestrationRequest,
        plugin_result: PluginDispatchResult | None,
        reflection: str,
    ) -> List[MemoryUpdate]:
        summary = reflection or f"Request {request.intent} completed"
        annotations: Dict[str, str] = {
            "intent": request.intent,
            "channel": request.channel,
            "memory_provider": self.provider,
        }
        if plugin_result:
            annotations["dispatch_count"] = str(plugin_result.dispatched_count)
            annotations["plugin"] = plugin_result.plugin_name
        return [
            MemoryUpdate(
                summary=summary,
                annotations=annotations,
                tokens_used=len(summary.split()),
            )
        ]

    async def commit_updates(
        self,
        request: OrchestrationRequest,
        updates: List[MemoryUpdate],
    ) -> None:
        if not updates or not self._graphiti.enabled:
            return

        group_id = self._derive_group_id(request)
        payload = {
            "request_id": request.request_id,
            "intent": request.intent,
            "channel": request.channel,
            "audience": request.audience.model_dump() if request.audience else None,
            "metadata": request.metadata,
        }

        for update in updates:
            try:
                await self._graphiti.record_memory_update(
                    summary=update.summary,
                    annotations=update.annotations,
                    request_payload=payload,
                    group_id=group_id,
                )
            except Exception as exc:  # pragma: no cover - network failures
                self._logger.warning("Failed to persist memory update to Graphiti: %s", exc)

    def _derive_group_id(self, request: OrchestrationRequest) -> Optional[str]:
        metadata = request.metadata or {}
        group = None
        if isinstance(metadata.get("graphiti"), dict):
            graphiti_meta = metadata["graphiti"]
            group = graphiti_meta.get("group_id")
        group = group or metadata.get("graphiti_group_id")
        if not group and request.audience:
            group = request.audience.segment_id
        return group or self._graphiti.default_group_id


@lru_cache(maxsize=1)
def get_memory_service() -> MemoryService:
    return MemoryService()
