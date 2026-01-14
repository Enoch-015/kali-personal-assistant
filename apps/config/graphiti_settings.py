"""Graphiti knowledge graph configuration settings."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class GraphitiSettings(BaseModel):
    """Graphiti knowledge graph and LLM provider configuration."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    # Core settings
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
    
    # Neo4j connection
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
    
    # Graphiti options
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
    
    # ========== OpenAI ==========
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
    
    # ========== Azure OpenAI ==========
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
    
    # ========== Gemini ==========
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
    
    # ========== Anthropic ==========
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
    
    # ========== Groq ==========
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
    
    # ========== Ollama ==========
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
    
    # ========== Generic OpenAI-compatible ==========
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

    # ========== Credential validation ==========
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
