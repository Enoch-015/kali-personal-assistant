from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Literal, Optional

from dotenv import dotenv_values
from pydantic import AliasChoices, BaseModel, Field, RedisDsn, ValidationInfo, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_redis_url() -> RedisDsn:
    return RedisDsn("redis://localhost:6379/0")


class RedisSettings(BaseModel):
    url: RedisDsn = Field(
        default_factory=_default_redis_url,
        description="Connection string for the Redis instance used as the event bus.",
    )
    channel_prefix: str = Field(
        default="kali",
        description="Prefix applied to Redis Pub/Sub channels for namespacing.",
    )
    request_channel: str = Field(
        default="agent.requests",
        description="Channel used for inbound orchestration requests.",
    )
    status_channel: str = Field(
        default="agent.status",
        description="Channel used for publishing orchestration status updates.",
    )
    max_connections: int = Field(default=20, ge=1, le=200)

    @property
    def namespaced_request_channel(self) -> str:
        return f"{self.channel_prefix}:{self.request_channel}".lower()

    @property
    def namespaced_status_channel(self) -> str:
        return f"{self.channel_prefix}:{self.status_channel}".lower()


class MongoSettings(BaseModel):
    enabled: bool = Field(
        default=True,
        description="Enable MongoDB-backed policy storage when true.",
        validation_alias=AliasChoices("MONGO_ENABLED", "mongo_enabled"),
    )
    uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string used for policy persistence.",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI", "mongo_uri"),
    )
    database: str = Field(
        default="kali_policy",
        description="MongoDB database name for policy storage.",
        validation_alias=AliasChoices("MONGO_DATABASE", "mongo_database"),
    )
    policies_collection: str = Field(
        default="policy_directives",
        description="MongoDB collection used to persist policy directives.",
        validation_alias=AliasChoices("MONGO_POLICIES_COLLECTION", "mongo_policies_collection"),
    )
    server_selection_timeout_ms: int = Field(
        default=250,
        ge=50,
        le=10000,
        description="Timeout in milliseconds for selecting a MongoDB server.",
        validation_alias=AliasChoices(
            "MONGO_SERVER_SELECTION_TIMEOUT_MS",
            "mongo_server_selection_timeout_ms",
        ),
    )


class SMTPSettings(BaseModel):
    host: str = Field(default="localhost", description="SMTP server hostname")
    port: int = Field(default=1025, ge=1, le=65535, description="SMTP server port")
    username: Optional[str] = Field(default=None, description="SMTP username for authentication")
    password: Optional[str] = Field(default=None, description="SMTP password for authentication")
    use_tls: bool = Field(default=False, description="Upgrade connection to TLS via STARTTLS")
    use_ssl: bool = Field(default=False, description="Establish SMTP connection over SSL")
    timeout: float = Field(default=10.0, ge=1.0, le=60.0, description="Socket timeout in seconds")
    from_address: Optional[str] = Field(
        default="no-reply@kali.local",
        description="Default sender email address if not provided in a request",
    )
    default_recipient: Optional[str] = Field(
        default=None,
        description="Fallback recipient when none are provided by the request",
    )
    deliver: bool = Field(
        default=False,
        description="Send messages via SMTP when true; otherwise run in dry-run mode.",
    )


class LangGraphSettings(BaseModel):
    checkpoint_store: Literal["memory", "sqlite"] = Field(default="memory")
    checkpoint_path: str = Field(
        default=".langgraph/checkpoints.sqlite",
        description="Path used when checkpoint_store is set to 'sqlite'.",
    )
    max_concurrency: int = Field(default=32, ge=1, le=256)


class GraphitiSettings(BaseModel):
    enabled: bool = Field(
        default=False,
        description="Enable Graphiti knowledge graph integration when credentials are provided.",
        validation_alias=AliasChoices("GRAPHITI_ENABLED", "graphiti_enabled"),
    )
    llm_provider: Literal["openai", "gemini", "azure", "anthropic", "groq", "ollama", "generic"] = Field(
        default="openai",
        description="Primary LLM provider used by Graphiti.",
        validation_alias=AliasChoices("GRAPHITI_LLM_PROVIDER", "GRAPHITI_PROVIDER", "LLM_PROVIDER"),
    )
    neo4j_uri: Optional[str] = Field(
        default=None,
        description="Neo4j connection URI used by Graphiti.",
        validation_alias=AliasChoices("GRAPHITI_NEO4J_URI", "NEO4J_URI"),
    )
    neo4j_user: Optional[str] = Field(
        default=None,
        description="Neo4j username used by Graphiti.",
        validation_alias=AliasChoices("GRAPHITI_NEO4J_USER", "NEO4J_USER"),
    )
    neo4j_password: Optional[str] = Field(
        default=None,
        description="Neo4j password used by Graphiti.",
        validation_alias=AliasChoices("GRAPHITI_NEO4J_PASSWORD", "NEO4J_PASSWORD"),
    )
    group_id: Optional[str] = Field(
        default=None,
        description="Default Graphiti group namespace applied to episodes.",
        validation_alias=AliasChoices("GRAPHITI_GROUP_ID", "GROUP_ID"),
    )
    build_indices_on_startup: bool = Field(
        default=False,
        description="Run Graphiti index/constraint builder on first use.",
        validation_alias=AliasChoices("GRAPHITI_BUILD_INDICES", "GRAPHITI_BUILD_INDEXES"),
    )
    search_limit: int = Field(
        default=5,
        ge=1,
        le=64,
        description="Default number of Graphiti search results to retrieve for context.",
        validation_alias=AliasChoices("GRAPHITI_SEARCH_LIMIT", "GRAPHITI_SEARCH_RESULTS_LIMIT"),
    )
    # OpenAI  
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key.",
        validation_alias=AliasChoices("OPENAI_API_KEY", "GRAPHITI_OPENAI_API_KEY"),
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model name.",
        validation_alias=AliasChoices("OPENAI_MODEL", "GRAPHITI_OPENAI_MODEL"),
    )
    openai_small_model: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI small model name.",
        validation_alias=AliasChoices("OPENAI_SMALL_MODEL", "GRAPHITI_OPENAI_SMALL_MODEL"),
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model name.",
        validation_alias=AliasChoices("OPENAI_EMBEDDING_MODEL", "GRAPHITI_OPENAI_EMBEDDING_MODEL"),
    )
    # Azure OpenAI
    azure_openai_endpoint: Optional[str] = Field(
        default=None,
        description="Azure OpenAI LLM endpoint URL.",
        validation_alias=AliasChoices("AZURE_OPENAI_ENDPOINT"),
    )
    azure_openai_deployment_name: Optional[str] = Field(
        default=None,
        description="Azure OpenAI LLM deployment name.",
        validation_alias=AliasChoices("AZURE_OPENAI_DEPLOYMENT_NAME"),
    )
    azure_openai_api_version: Optional[str] = Field(
        default=None,
        description="Azure OpenAI API version.",
        validation_alias=AliasChoices("AZURE_OPENAI_API_VERSION"),
    )
    azure_openai_embedding_api_key: Optional[str] = Field(
        default=None,
        description="Azure OpenAI Embedding deployment key.",
        validation_alias=AliasChoices("AZURE_OPENAI_EMBEDDING_API_KEY"),
    )
    azure_openai_embedding_endpoint: Optional[str] = Field(
        default=None,
        description="Azure OpenAI Embedding endpoint URL.",
        validation_alias=AliasChoices("AZURE_OPENAI_EMBEDDING_ENDPOINT"),
    )
    azure_openai_embedding_deployment_name: Optional[str] = Field(
        default=None,
        description="Azure OpenAI embedding deployment name.",
        validation_alias=AliasChoices("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
    )
    azure_openai_embedding_api_version: Optional[str] = Field(
        default=None,
        description="Azure OpenAI embedding API version.",
        validation_alias=AliasChoices("AZURE_OPENAI_EMBEDDING_API_VERSION"),
    )
    azure_openai_use_managed_identity: Optional[bool] = Field(
        default=None,
        description="Use Azure Managed Identities for authentication.",
        validation_alias=AliasChoices("AZURE_OPENAI_USE_MANAGED_IDENTITY"),
    )
    # Gemini
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key used when llm_provider is set to 'gemini'.",
        validation_alias=AliasChoices("GRAPHITI_GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model name for primary LLM usage.",
        validation_alias=AliasChoices("GRAPHITI_GEMINI_MODEL", "GEMINI_MODEL"),
    )
    gemini_embedding_model: str = Field(
        default="embedding-001",
        description="Gemini embedding model identifier.",
        validation_alias=AliasChoices("GRAPHITI_GEMINI_EMBEDDING_MODEL", "GEMINI_EMBEDDING_MODEL"),
    )
    gemini_reranker_model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini model used for cross-encoding / reranking.",
        validation_alias=AliasChoices("GRAPHITI_GEMINI_RERANKER_MODEL", "GEMINI_RERANKER_MODEL"),
    )
    # Anthropic
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key.",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "GRAPHITI_ANTHROPIC_API_KEY"),
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Anthropic model name.",
        validation_alias=AliasChoices("ANTHROPIC_MODEL", "GRAPHITI_ANTHROPIC_MODEL"),
    )
    anthropic_small_model: str = Field(
        default="claude-3-5-haiku-20241022",
        description="Anthropic small model name.",
        validation_alias=AliasChoices("ANTHROPIC_SMALL_MODEL", "GRAPHITI_ANTHROPIC_SMALL_MODEL"),
    )
    # Groq
    groq_api_key: Optional[str] = Field(
        default=None,
        description="Groq API key.",
        validation_alias=AliasChoices("GROQ_API_KEY", "GRAPHITI_GROQ_API_KEY"),
    )
    groq_model: str = Field(
        default="llama-3.1-70b-versatile",
        description="Groq model name.",
        validation_alias=AliasChoices("GROQ_MODEL", "GRAPHITI_GROQ_MODEL"),
    )
    groq_small_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Groq small model name.",
        validation_alias=AliasChoices("GROQ_SMALL_MODEL", "GRAPHITI_GROQ_SMALL_MODEL"),
    )
    # Ollama
    ollama_base_url: Optional[str] = Field(
        default="http://localhost:11434/v1",
        description="Ollama base URL.",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "GRAPHITI_OLLAMA_BASE_URL"),
    )
    ollama_model: str = Field(
        default="deepseek-r1:7b",
        description="Ollama LLM model name.",
        validation_alias=AliasChoices("OLLAMA_MODEL", "GRAPHITI_OLLAMA_MODEL"),
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model name.",
        validation_alias=AliasChoices("OLLAMA_EMBEDDING_MODEL", "GRAPHITI_OLLAMA_EMBEDDING_MODEL"),
    )
    ollama_embedding_dim: int = Field(
        default=768,
        description="Ollama embedding dimension.",
        validation_alias=AliasChoices("OLLAMA_EMBEDDING_DIM", "GRAPHITI_OLLAMA_EMBEDDING_DIM"),
    )
    # Generic OpenAI-compatible
    generic_api_key: Optional[str] = Field(
        default=None,
        description="Generic OpenAI-compatible API key.",
        validation_alias=AliasChoices("GENERIC_API_KEY", "GRAPHITI_GENERIC_API_KEY"),
    )
    generic_model: str = Field(
        default="mistral-large-latest",
        description="Generic OpenAI-compatible model name.",
        validation_alias=AliasChoices("GENERIC_MODEL", "GRAPHITI_GENERIC_MODEL"),
    )
    generic_small_model: str = Field(
        default="mistral-small-latest",
        description="Generic OpenAI-compatible small model name.",
        validation_alias=AliasChoices("GENERIC_SMALL_MODEL", "GRAPHITI_GENERIC_SMALL_MODEL"),
    )
    generic_base_url: Optional[str] = Field(
        default=None,
        description="Generic OpenAI-compatible base URL.",
        validation_alias=AliasChoices("GENERIC_BASE_URL", "GRAPHITI_GENERIC_BASE_URL"),
    )
    generic_embedding_model: str = Field(
        default="mistral-embed",
        description="Generic OpenAI-compatible embedding model name.",
        validation_alias=AliasChoices("GENERIC_EMBEDDING_MODEL", "GRAPHITI_GENERIC_EMBEDDING_MODEL"),
    )

    def _base_credentials_ready(self) -> bool:
        return bool(self.neo4j_uri and self.neo4j_user and self.neo4j_password)

    def _llm_credentials_ready(self) -> bool:
        provider = (self.llm_provider or "openai").lower()
        if provider == "openai":
            return bool(self.openai_api_key)
        if provider == "azure":
            has_llm = bool(
                self.openai_api_key
                and self.azure_openai_endpoint
                and self.azure_openai_deployment_name
                and self.azure_openai_api_version
            )
            has_embedder = bool(
                self.azure_openai_embedding_endpoint
                and self.azure_openai_embedding_deployment_name
                and self.azure_openai_embedding_api_version
                and (self.azure_openai_embedding_api_key or self.azure_openai_use_managed_identity)
            )
            return has_llm and has_embedder
        if provider == "gemini":
            return bool(self.gemini_api_key)
        if provider == "anthropic":
            return bool(self.anthropic_api_key and self.openai_api_key)
        if provider == "groq":
            return bool(self.groq_api_key and self.openai_api_key)
        if provider == "ollama":
            return bool(self.ollama_base_url and self.ollama_model and self.ollama_embedding_model)
        if provider == "generic":
            return bool(self.generic_api_key and self.generic_base_url)
        return False

    @property
    def has_credentials(self) -> bool:
        return self._base_credentials_ready() and self._llm_credentials_ready()


_ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="allow",
    )

    environment: Literal["development", "production", "test"] = Field(
        default="development",
        description="Active runtime environment. Influences default Redis selection.",
        validation_alias=AliasChoices("AI_ENV", "environment"),
    )
    redis: RedisSettings = Field(default_factory=RedisSettings)
    mongo: MongoSettings = Field(default_factory=MongoSettings)
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    review_max_retries: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Number of times the review agent may retry a workflow before escalating.",
    )
    redis_url_override: Optional[RedisDsn] = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    langgraph: LangGraphSettings = Field(default_factory=LangGraphSettings)
    graphiti: GraphitiSettings = Field(default_factory=GraphitiSettings)

    @model_validator(mode="after")
    def _configure_integrations(self) -> "Settings":
        graphiti_env_overrides = self._extract_graphiti_env_overrides()
        if graphiti_env_overrides:
            self.graphiti = self.graphiti.model_copy(update=graphiti_env_overrides)

        if self.environment == "production":
            candidate = self.redis_url_override or self.redis.url
            self.redis = self.redis.model_copy(update={"url": candidate})
        else:
            self.redis = self.redis.model_copy(update={"url": _default_redis_url()})

        graphiti_update = {}
        if self.graphiti.has_credentials and not self.graphiti.enabled:
            graphiti_update["enabled"] = True
        if self.graphiti.enabled and not self.graphiti.has_credentials:
            graphiti_update["enabled"] = False
        if graphiti_update:
            self.graphiti = self.graphiti.model_copy(update=graphiti_update)
        return self

    @property
    def redis_url(self) -> RedisDsn:
        return self.redis.url

    @property
    def graphiti_enabled(self) -> bool:
        return self.graphiti.enabled and self.graphiti.has_credentials

    def _extract_graphiti_env_overrides(self) -> dict[str, Any]:
        extras: dict[str, Any] = getattr(self, "model_extra", {}) or {}

        def coerce_bool(value: Any) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
            return bool(value)

        def coerce_str(value: Any) -> str:
            return str(value).strip()

        mapping: dict[str, tuple[str, Callable[[Any], Any]]] = {
            # General
            "graphiti_enabled": ("enabled", coerce_bool),
            "graphiti_llm_provider": ("llm_provider", coerce_str),
            "graphiti_provider": ("llm_provider", coerce_str),
            "llm_provider": ("llm_provider", coerce_str),
            "graphiti_neo4j_uri": ("neo4j_uri", coerce_str),
            "neo4j_uri": ("neo4j_uri", coerce_str),
            "graphiti_neo4j_user": ("neo4j_user", coerce_str),
            "neo4j_user": ("neo4j_user", coerce_str),
            "graphiti_neo4j_password": ("neo4j_password", coerce_str),
            "neo4j_password": ("neo4j_password", coerce_str),
            "graphiti_group_id": ("group_id", coerce_str),
            "group_id": ("group_id", coerce_str),
            "graphiti_build_indices": ("build_indices_on_startup", coerce_bool),
            "graphiti_build_indexes": ("build_indices_on_startup", coerce_bool),
            "graphiti_search_limit": ("search_limit", lambda v: int(str(v))),
            "graphiti_search_results_limit": ("search_limit", lambda v: int(str(v))),
            # OpenAI
            "openai_api_key": ("openai_api_key", coerce_str),
            "graphiti_openai_api_key": ("openai_api_key", coerce_str),
            "open_ai_key": ("openai_api_key", coerce_str),
            "openai_model": ("openai_model", coerce_str),
            "graphiti_openai_model": ("openai_model", coerce_str),
            "openai_small_model": ("openai_small_model", coerce_str),
            "graphiti_openai_small_model": ("openai_small_model", coerce_str),
            "openai_embedding_model": ("openai_embedding_model", coerce_str),
            "graphiti_openai_embedding_model": ("openai_embedding_model", coerce_str),
            # Azure OpenAI
            "azure_openai_endpoint": ("azure_openai_endpoint", coerce_str),
            "azure_openai_deployment_name": ("azure_openai_deployment_name", coerce_str),
            "azure_openai_api_version": ("azure_openai_api_version", coerce_str),
            "azure_openai_embedding_api_key": ("azure_openai_embedding_api_key", coerce_str),
            "azure_openai_embedding_endpoint": ("azure_openai_embedding_endpoint", coerce_str),
            "azure_openai_embedding_deployment_name": ("azure_openai_embedding_deployment_name", coerce_str),
            "azure_openai_embedding_api_version": ("azure_openai_embedding_api_version", coerce_str),
            "azure_openai_use_managed_identity": ("azure_openai_use_managed_identity", coerce_bool),
            # Gemini
            "graphiti_gemini_api_key": ("gemini_api_key", coerce_str),
            "google_api_key": ("gemini_api_key", coerce_str),
            "graphiti_gemini_model": ("gemini_model", coerce_str),
            "gemini_model": ("gemini_model", coerce_str),
            "graphiti_gemini_embedding_model": ("gemini_embedding_model", coerce_str),
            "gemini_embedding_model": ("gemini_embedding_model", coerce_str),
            "graphiti_gemini_reranker_model": ("gemini_reranker_model", coerce_str),
            "gemini_reranker_model": ("gemini_reranker_model", coerce_str),
            # Anthropic
            "anthropic_api_key": ("anthropic_api_key", coerce_str),
            "graphiti_anthropic_api_key": ("anthropic_api_key", coerce_str),
            "anthropic_model": ("anthropic_model", coerce_str),
            "graphiti_anthropic_model": ("anthropic_model", coerce_str),
            "anthropic_small_model": ("anthropic_small_model", coerce_str),
            "graphiti_anthropic_small_model": ("anthropic_small_model", coerce_str),
            # Groq
            "groq_api_key": ("groq_api_key", coerce_str),
            "graphiti_groq_api_key": ("groq_api_key", coerce_str),
            "groq_model": ("groq_model", coerce_str),
            "graphiti_groq_model": ("groq_model", coerce_str),
            "groq_small_model": ("groq_small_model", coerce_str),
            "graphiti_groq_small_model": ("groq_small_model", coerce_str),
            # Ollama
            "ollama_base_url": ("ollama_base_url", coerce_str),
            "graphiti_ollama_base_url": ("ollama_base_url", coerce_str),
            "ollama_model": ("ollama_model", coerce_str),
            "graphiti_ollama_model": ("ollama_model", coerce_str),
            "ollama_embedding_model": ("ollama_embedding_model", coerce_str),
            "graphiti_ollama_embedding_model": ("ollama_embedding_model", coerce_str),
            "ollama_embedding_dim": ("ollama_embedding_dim", lambda v: int(str(v))),
            "graphiti_ollama_embedding_dim": ("ollama_embedding_dim", lambda v: int(str(v))),
            # Generic OpenAI-compatible
            "generic_api_key": ("generic_api_key", coerce_str),
            "graphiti_generic_api_key": ("generic_api_key", coerce_str),
            "generic_model": ("generic_model", coerce_str),
            "graphiti_generic_model": ("generic_model", coerce_str),
            "generic_small_model": ("generic_small_model", coerce_str),
            "graphiti_generic_small_model": ("generic_small_model", coerce_str),
            "generic_base_url": ("generic_base_url", coerce_str),
            "graphiti_generic_base_url": ("generic_base_url", coerce_str),
            "generic_embedding_model": ("generic_embedding_model", coerce_str),
            "graphiti_generic_embedding_model": ("generic_embedding_model", coerce_str),
        }

        overrides: dict[str, Any] = {}
        extras_lower = {(key or "").lower(): value for key, value in extras.items() if value is not None}
        env_file_values: dict[str, Any] = {}
        if _ENV_FILE_PATH.exists():
            try:
                env_file_values = {
                    (key or "").lower(): value
                    for key, value in (dotenv_values(_ENV_FILE_PATH) or {}).items()
                    if value is not None
                }
            except Exception:
                env_file_values = {}
        for alias, (field_name, transform) in mapping.items():
            value = extras_lower.get(alias)
            if value is None:
                env_key = alias.upper()
                if env_key in os.environ:
                    value = os.environ[env_key]
            if value is None:
                value = env_file_values.get(alias)
            if value is None:
                continue
            try:
                overrides[field_name] = transform(value)
            except Exception:
                continue
        return overrides


def get_settings(override: Optional[dict] = None) -> Settings:
    return Settings(**(override or {}))
