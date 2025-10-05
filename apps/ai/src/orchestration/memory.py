from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

from .models import MemorySnapshot, MemoryUpdate, OrchestrationRequest, PluginDispatchResult


class MemoryService:
    """Demo memory provider that simulates reads and writes.

    Replace these methods with real integrations (Redis, Neo4j, vector DB, etc.).
    """

    def retrieve_context(self, request: OrchestrationRequest) -> MemorySnapshot:
        base_snippets: List[str] = [
            "[demo] No persistent memory connected yet.",
            f"[demo] Last intent observed: {request.intent}",
        ]
        graph_relations: List[str] = [
            "[demo] Placeholder relationship graph node"
        ]
        vector_results: List[str] = [
            "[demo] Vector search results not available."
        ]
        return MemorySnapshot(
            memory_snippets=base_snippets,
            graph_relations=graph_relations,
            vector_results=vector_results,
            freshness_seconds=5,
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
        annotations: Dict[str, str] = {"intent": request.intent}
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

    async def commit_updates(self, updates: List[MemoryUpdate]) -> None:
        # Replace with integration to persistence
        return None


@lru_cache(maxsize=1)
def get_memory_service() -> MemoryService:
    return MemoryService()
