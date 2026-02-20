"""Graphiti knowledge-graph configuration using provider registries.

``GraphitiSettings`` keeps common Graphiti options (search tuning, build flags)
while delegating:
* **LLM** to a discriminated union of ``BaseLLMProvider`` subclasses.
* **Graph store** to a discriminated union of ``BaseGraphStore`` subclasses.

Only the *selected* provider's fields are validated.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# ── LLM providers ───────────────────────────────────────────
from ..providers.llm.anthropic import AnthropicProvider
from ..providers.llm.azure import AzureOpenAIProvider
from ..providers.llm.base import BaseLLMProvider
from ..providers.llm.gemini import GeminiProvider
from ..providers.llm.generic import GenericProvider
from ..providers.llm.groq import GroqProvider
from ..providers.llm.ollama import OllamaProvider
from ..providers.llm.openai import OpenAIProvider

# ── Graph store providers ───────────────────────────────────
from ..providers.graph_stores.base import BaseGraphStore
from ..providers.graph_stores.neo4j import Neo4jStore

# Discriminated unions
LLMProvider = Annotated[
    Union[
        OpenAIProvider,
        GeminiProvider,
        AnthropicProvider,
        GroqProvider,
        OllamaProvider,
        AzureOpenAIProvider,
        GenericProvider,
    ],
    Field(discriminator="provider"),
]

GraphStoreProvider = Annotated[
    Union[Neo4jStore],
    Field(discriminator="provider"),
]


class GraphitiSettings(BaseModel):
    """Graphiti knowledge graph and LLM provider configuration.

    Both ``llm`` and ``graph_store`` are ``None`` until configured.
    Setting them triggers Pydantic's discriminated-union validation which
    only checks the fields for the *chosen* provider.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Core settings
    enabled: bool = Field(
        default=False,
        description="Enable Graphiti knowledge graph integration.",
    )

    # Graphiti options
    group_id: Optional[str] = Field(
        default=None, description="Default Graphiti group namespace applied to episodes."
    )
    build_indices_on_startup: bool = Field(
        default=False,
        description="Run Graphiti index/constraint builder on first use.",
    )
    search_limit: int = Field(
        default=5,
        ge=1,
        le=64,
        description="Default number of Graphiti search results to retrieve.",
    )

    # LLM provider (discriminated union)
    llm: Optional[LLMProvider] = Field(
        default=None,
        description="LLM provider settings. Only the selected provider is validated.",
    )

    # Graph store (discriminated union)
    graph_store: Optional[GraphStoreProvider] = Field(
        default=None,
        description="Graph database provider. Only the selected store is validated.",
    )

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def llm_provider(self) -> str | None:
        """Return the active LLM provider name, or ``None``."""
        return self.llm.provider if self.llm else None

    @property
    def graph_store_provider(self) -> str | None:
        """Return the active graph store provider name, or ``None``."""
        return self.graph_store.provider if self.graph_store else None

    @property
    def has_graph_store(self) -> bool:
        return self.graph_store is not None and self.graph_store.is_configured

    @property
    def has_llm(self) -> bool:
        return self.llm is not None and self.llm.is_configured

    @property
    def has_credentials(self) -> bool:
        """``True`` when both graph store *and* the LLM provider are fully configured."""
        return self.has_graph_store and self.has_llm

    # Backward-compat: Neo4j fields (delegate to graph_store)
    @property
    def neo4j_uri(self) -> str | None:
        if self.graph_store and self.graph_store.provider == "neo4j":
            return self.graph_store.uri  # type: ignore[union-attr]
        return None

    @property
    def neo4j_user(self) -> str | None:
        if self.graph_store and self.graph_store.provider == "neo4j":
            return self.graph_store.user  # type: ignore[union-attr]
        return None

    @property
    def neo4j_password(self) -> str | None:
        if self.graph_store and self.graph_store.provider == "neo4j":
            return self.graph_store.password  # type: ignore[union-attr]
        return None

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_vault(
        cls,
        *,
        ai_secrets: dict[str, Any],
        db_secrets: dict[str, Any],
    ) -> "GraphitiSettings":
        """Build ``GraphitiSettings`` entirely from Vault data.

        Parameters
        ----------
        ai_secrets:
            Vault ``python-ai`` path (contains LLM provider name, API keys,
            model names, graphiti options).
        db_secrets:
            Vault ``databases`` path (contains Neo4j URI, credentials).
        """
        # LLM
        provider_name = (
            ai_secrets.get("graphiti-llm-provider")
            or ai_secrets.get("llm-provider")
            or "openai"
        ).lower()
        llm_cls = BaseLLMProvider._registry.get(provider_name)
        llm_instance = llm_cls.from_vault(ai_secrets) if llm_cls else None

        # Graph store
        store_name = (
            ai_secrets.get("graphiti-graph-store")
            or ai_secrets.get("graph-store")
            or "neo4j"
        ).lower()
        store_cls = BaseGraphStore._registry.get(store_name)
        store_instance = store_cls.from_vault(db_secrets) if store_cls else None

        enabled = bool(
            llm_instance and llm_instance.is_configured
            and store_instance and store_instance.is_configured
        )

        return cls(
            enabled=enabled,
            group_id=ai_secrets.get("graphiti-group-id"),
            build_indices_on_startup=_to_bool(
                ai_secrets.get("graphiti-build-indices", False)
            ),
            search_limit=int(ai_secrets.get("graphiti-search-limit", 5)),
            llm=llm_instance,
            graph_store=store_instance,
        )

    @classmethod
    def from_env(
        cls,
        env: dict[str, Any],
        *,
        provider: str | None = None,
        graph_store: str | None = None,
    ) -> "GraphitiSettings":
        """Build from an env-dict (model_extra / os.environ merge)."""
        from ..utils import coerce_bool

        provider = (
            provider
            or env.get("graphiti_llm_provider")
            or env.get("GRAPHITI_LLM_PROVIDER")
            or env.get("llm_provider")
            or env.get("LLM_PROVIDER")
        )

        llm_instance: BaseLLMProvider | None = None
        if provider:
            provider = provider.lower()
            llm_cls = BaseLLMProvider._registry.get(provider)
            if llm_cls is not None:
                llm_instance = llm_cls.from_env(env)

        graph_store_name = (
            graph_store
            or env.get("graphiti_graph_store")
            or env.get("GRAPHITI_GRAPH_STORE")
            or "neo4j"
        ).lower()
        store_instance: BaseGraphStore | None = None
        store_cls = BaseGraphStore._registry.get(graph_store_name)
        if store_cls is not None:
            store_instance = store_cls.from_env(env)

        return cls(
            enabled=coerce_bool(
                env.get("graphiti_enabled")
                or env.get("GRAPHITI_ENABLED")
                or (llm_instance is not None)
            ),
            group_id=env.get("graphiti_group_id") or env.get("GROUP_ID"),
            build_indices_on_startup=coerce_bool(
                env.get("graphiti_build_indices")
                or env.get("GRAPHITI_BUILD_INDICES")
                or False
            ),
            search_limit=int(
                env.get("graphiti_search_limit")
                or env.get("GRAPHITI_SEARCH_LIMIT")
                or 5
            ),
            llm=llm_instance,
            graph_store=store_instance,
        )


def _to_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "on"}
    return bool(val)
