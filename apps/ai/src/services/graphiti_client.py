from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from config.settings import Settings, get_settings

try:  # pragma: no cover - optional dependency handling
    from graphiti_core import Graphiti as GraphitiSDK  # type: ignore[import-not-found]
    from graphiti_core.nodes import EpisodeType as GraphitiEpisodeType  # type: ignore[import-not-found]
    from graphiti_core.search.search_config_recipes import (  # type: ignore[import-not-found]
        NODE_HYBRID_SEARCH_RRF,
    )
except ImportError:  # pragma: no cover - handled gracefully at runtime
    GraphitiSDK = None  # type: ignore[assignment]
    GraphitiEpisodeType = None  # type: ignore[assignment]
    NODE_HYBRID_SEARCH_RRF = None  # type: ignore[assignment]

try:  # pragma: no cover - optional Gemini extras
    from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig as GeminiLLMConfig  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - handled gracefully at runtime
    GeminiClient = None  # type: ignore[assignment]
    GeminiLLMConfig = None  # type: ignore[assignment]

try:  # pragma: no cover - optional Gemini extras
    from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - handled gracefully at runtime
    GeminiEmbedder = None  # type: ignore[assignment]
    GeminiEmbedderConfig = None  # type: ignore[assignment]

try:  # pragma: no cover - optional Gemini extras
    from graphiti_core.cross_encoder.gemini_reranker_client import (  # type: ignore[import-not-found]
        GeminiRerankerClient,
    )
except ImportError:  # pragma: no cover - handled gracefully at runtime
    GeminiRerankerClient = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class GraphitiClient:
    """Thin wrapper around the Graphiti SDK with graceful fallbacks."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings("ai")
        self._enabled = GraphitiSDK is not None and self._settings.graphiti_enabled
        self._client: Optional[Any] = None
        self._lock = asyncio.Lock()
        self._indices_prepared = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def default_group_id(self) -> Optional[str]:
        return self._settings.graphiti.group_id

    def _build_client(self) -> Optional[Any]:
        if GraphitiSDK is None:
            return None

        graphiti_settings = self._settings.graphiti
        if not graphiti_settings.has_credentials:
            logger.warning("Graphiti credentials incomplete; disabling integration")
            return None

        neo4j_uri = graphiti_settings.neo4j_uri
        neo4j_user = graphiti_settings.neo4j_user
        neo4j_password = graphiti_settings.neo4j_password
        if not (neo4j_uri and neo4j_user and neo4j_password):
            logger.warning("Graphiti Neo4j credentials missing; disabling integration")
            return None

        provider = (graphiti_settings.llm_provider or "openai").lower()
        kwargs: Dict[str, Any] = {}

        if provider == "gemini":
            missing_components = []
            if GeminiClient is None or GeminiLLMConfig is None:
                missing_components.append("Gemini LLM client")
            if GeminiEmbedder is None or GeminiEmbedderConfig is None:
                missing_components.append("Gemini embedder")
            if missing_components:
                logger.warning(
                    "Graphiti Gemini support missing components: %s; run pip install graphiti-core[google-genai]",
                    ", ".join(missing_components),
                )
                return None
            if not graphiti_settings.gemini_api_key:
                logger.warning("Graphiti Gemini API key missing; set GOOGLE_API_KEY or GRAPHITI_GEMINI_API_KEY")
                return None

            llm_config = cast(Any, GeminiLLMConfig)(
                api_key=graphiti_settings.gemini_api_key,
                model=graphiti_settings.gemini_model,
            )
            embedder_config = cast(Any, GeminiEmbedderConfig)(
                api_key=graphiti_settings.gemini_api_key,
                embedding_model=graphiti_settings.gemini_embedding_model,
            )

            kwargs.update(
                llm_client=cast(Any, GeminiClient)(config=llm_config),
                embedder=cast(Any, GeminiEmbedder)(config=embedder_config),
            )
            if GeminiRerankerClient is not None and GeminiLLMConfig is not None:
                reranker_config = cast(Any, GeminiLLMConfig)(
                    api_key=graphiti_settings.gemini_api_key,
                    model=graphiti_settings.gemini_reranker_model,
                )
                kwargs["cross_encoder"] = cast(Any, GeminiRerankerClient)(config=reranker_config)
            else:
                logger.info("Graphiti Gemini reranker client not available; continuing without cross encoder")
        elif provider not in {"openai", "azure", "anthropic", "groq", "ollama", "generic"}:
            logger.warning("Unsupported Graphiti LLM provider '%s'", provider)
            return None

        try:
            return GraphitiSDK(  # type: ignore[call-arg]
                neo4j_uri,
                neo4j_user,
                neo4j_password,
                **kwargs,
            )
        except Exception as exc:  # pragma: no cover - network/setup failures
            logger.warning("Failed to initialize Graphiti client: %s", exc)
            return None

    async def _ensure_client(self) -> Optional[Any]:
        if not self._enabled:
            return None
        if self._client is not None:
            return self._client
        if GraphitiSDK is None:  # pragma: no cover - import guard
            self._enabled = False
            return None

        async with self._lock:
            if self._client is not None:
                return self._client
            try:
                self._client = self._build_client()
                if (
                    self._client is not None
                    and self._settings.graphiti.build_indices_on_startup
                    and not self._indices_prepared
                ):
                    await self._client.build_indices_and_constraints()
                    self._indices_prepared = True
            except Exception as exc:  # pragma: no cover - network failures
                logger.warning("Graphiti initialization failed: %s", exc)
                self._client = None
                self._enabled = False
            if self._client is None:
                self._enabled = False
            return self._client

    async def search_facts(
        self,
        query: str,
        *,
        center_node_uuid: Optional[str] = None,
        group_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        client = await self._ensure_client()
        if client is None:
            return []

        kwargs: Dict[str, Any] = {"query": query}
        if center_node_uuid:
            kwargs["center_node_uuid"] = center_node_uuid
        if group_id:
            kwargs["group_id"] = group_id
        if limit or self._settings.graphiti.search_limit:
            kwargs["num_results"] = limit or self._settings.graphiti.search_limit

        try:
            results = await client.search(**kwargs)
        except Exception as exc:  # pragma: no cover - remote failure path
            logger.warning("Graphiti fact search failed: %s", exc)
            return []

        facts: List[str] = []
        for item in results or []:
            fact = getattr(item, "fact", None)
            if isinstance(fact, str) and fact.strip():
                facts.append(fact.strip())
        return facts

    async def search_nodes(
        self,
        query: str,
        *,
        group_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        client = await self._ensure_client()
        if client is None or NODE_HYBRID_SEARCH_RRF is None:
            return []

        config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        config.limit = limit or self._settings.graphiti.search_limit

        kwargs: Dict[str, Any] = {"query": query, "config": config}
        if group_id:
            kwargs["group_id"] = group_id

        try:
            results = await client._search(**kwargs)
        except Exception as exc:  # pragma: no cover - remote failure path
            logger.warning("Graphiti node search failed: %s", exc)
            return []

        nodes: List[str] = []
        for node in getattr(results, "nodes", []) or []:
            name = getattr(node, "name", "") or ""
            summary = getattr(node, "summary", "") or ""
            if name and summary:
                nodes.append(f"{name}: {summary}")
            elif summary:
                nodes.append(summary)
            elif name:
                nodes.append(name)
        return nodes

    async def add_episode(
        self,
        *,
        name: str,
        content: Any,
        description: str,
        group_id: Optional[str] = None,
        episode_type: Optional[str] = None,
        reference_time: Optional[datetime] = None,
    ) -> None:
        client = await self._ensure_client()
        if client is None or GraphitiEpisodeType is None:
            return

        ref = reference_time or datetime.now(timezone.utc)
        body = content
        inferred_type = GraphitiEpisodeType.text

        if episode_type and GraphitiEpisodeType is not None:
            with contextlib.suppress(KeyError, AttributeError):
                inferred_type = GraphitiEpisodeType[episode_type]
        elif isinstance(content, (dict, list)):
            try:
                body = json.dumps(content, default=str)
            except (TypeError, ValueError):
                body = json.dumps({"value": str(content)})
            inferred_type = GraphitiEpisodeType.json
        else:
            body = str(content)

        try:
            await client.add_episode(
                name=name,
                episode_body=body,
                source=inferred_type,
                source_description=description,
                reference_time=ref,
                group_id=group_id or self.default_group_id,
            )
        except Exception as exc:  # pragma: no cover - remote failure path
            logger.warning("Graphiti add_episode failed: %s", exc)

    async def record_memory_update(
        self,
        *,
        summary: str,
        annotations: Dict[str, Any],
        request_payload: Dict[str, Any],
        group_id: Optional[str] = None,
    ) -> None:
        episode_content = {
            "summary": summary,
            "annotations": annotations,
            "request": request_payload,
        }
        await self.add_episode(
            name=f"memory::{request_payload.get('request_id', 'unknown')}",
            content=episode_content,
            description="Agent memory update",
            group_id=group_id,
            episode_type="json",
        )

    async def close(self) -> None:
        client = self._client
        if client is None:
            return
        try:
            await client.close()
        except Exception:  # pragma: no cover - defensive
            pass
        finally:
            self._client = None
            self._enabled = False


graphiti_client_singleton: Optional[GraphitiClient] = None


def get_graphiti_client(settings: Optional[Settings] = None) -> GraphitiClient:
    global graphiti_client_singleton
    if graphiti_client_singleton is None:
        graphiti_client_singleton = GraphitiClient(settings=settings)
    return graphiti_client_singleton
