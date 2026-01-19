"""
Kali Personal Assistant - Unified Configuration Settings

This module provides a centralized configuration system that:
1. Loads shared base configuration from apps/config/.env
2. Overlays app-specific configuration from apps/{app_name}/.env
3. Supports environment variable overrides
4. Caches settings per app for performance

Usage:
    from config.settings import get_settings
    
    # In apps/ai/
    settings = get_settings("ai")
    
    # In apps/voice/
    settings = get_settings("voice")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Literal, Optional

from dotenv import dotenv_values, load_dotenv
from pydantic import AliasChoices, Field, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import all settings modules
from .graphiti_settings import GraphitiSettings
from .langgraph_settings import LangGraphSettings
from .livekit_settings import LiveKitSettings
from .mongo_settings import MongoSettings
from .redis_settings import RedisSettings
from .resend_settings import ResendSettings
from .utils import coerce_bool, coerce_int, coerce_str

# Re-export for backwards compatibility
__all__ = [
    "Settings",
    "RedisSettings",
    "MongoSettings",
    "ResendSettings",
    "LangGraphSettings",
    "GraphitiSettings",
    "LiveKitSettings",
    "get_settings",
    "clear_settings_cache",
]


# ============================================================
# Path Configuration
# ============================================================

_CONFIG_DIR = Path(__file__).resolve().parent
_APPS_DIR = _CONFIG_DIR.parent
_ENV_FILE_PATH = _CONFIG_DIR / ".env"  # Shared base config: apps/config/.env


def _get_app_env_path(app_name: str | None) -> Path | None:
    """Get the .env path for a specific app (ai, voice, etc.)."""
    if not app_name:
        return None
    app_dir = _APPS_DIR / app_name
    env_path = app_dir / ".env"
    return env_path if env_path.exists() else None


# ============================================================
# Main Settings Class
# ============================================================

class Settings(BaseSettings):
    """
    Unified settings for all Kali apps.
    
    Aggregates all subsystem configurations into a single settings object.
    Each app loads this with their specific .env overlay.
    """
    
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="allow",
    )

    # Core settings
    environment: Literal["development", "production", "test"] = Field(
        default="development",
        description="Active runtime environment. Influences default Redis selection.",
        validation_alias=AliasChoices("AI_ENV", "environment"),
    )
    
    # Subsystem configurations
    redis: RedisSettings = Field(default_factory=RedisSettings)
    mongo: MongoSettings = Field(default_factory=MongoSettings)
    resend: ResendSettings = Field(default_factory=ResendSettings)
    langgraph: LangGraphSettings = Field(default_factory=LangGraphSettings)
    graphiti: GraphitiSettings = Field(default_factory=GraphitiSettings)
    livekit: LiveKitSettings = Field(default_factory=LiveKitSettings)
    
    # Override fields
    redis_url_override: Optional[RedisDsn] = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    review_max_retries: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Number of times the review agent may retry a workflow before escalating.",
    )

    @model_validator(mode="after")
    def _configure_integrations(self) -> "Settings":
        """Post-validation hook to configure integrations based on env overrides."""
        # Apply Graphiti env overrides
        graphiti_env_overrides = self._extract_graphiti_env_overrides()
        if graphiti_env_overrides:
            self.graphiti = self.graphiti.model_copy(update=graphiti_env_overrides)

        # Apply Mongo env overrides
        mongo_env_overrides = self._extract_mongo_env_overrides()
        if mongo_env_overrides:
            self.mongo = self.mongo.model_copy(update=mongo_env_overrides)

        # Handle Redis URL override
        redis_update: dict[str, Any] | None = None
        if self.redis_url_override:
            redis_update = {"url": self.redis_url_override}
        elif self.environment == "production":
            redis_update = {"url": self.redis.url}

        if redis_update:
            self.redis = self.redis.model_copy(update=redis_update)

        # Disable Resend delivery if no API key
        if not self.resend.api_key and self.resend.deliver:
            self.resend = self.resend.model_copy(update={"deliver": False})

        # Auto-enable/disable Graphiti based on credentials
        graphiti_update = {}
        if self.graphiti.has_credentials and not self.graphiti.enabled:
            graphiti_update["enabled"] = True
        if self.graphiti.enabled and not self.graphiti.has_credentials:
            graphiti_update["enabled"] = False
        if graphiti_update:
            self.graphiti = self.graphiti.model_copy(update=graphiti_update)

        # Apply LiveKit env overrides
        livekit_env_overrides = self._extract_livekit_env_overrides()
        if livekit_env_overrides:
            self.livekit = self.livekit.model_copy(update=livekit_env_overrides)

        # Auto-disable LiveKit if no credentials
        if self.livekit.enabled and not self.livekit.has_credentials:
            self.livekit = self.livekit.model_copy(update={"enabled": False})
            
        return self

    # ============================================================
    # Convenience Properties
    # ============================================================
    
    @property
    def redis_url(self) -> RedisDsn:
        return self.redis.url

    @property
    def graphiti_enabled(self) -> bool:
        return self.graphiti.enabled and self.graphiti.has_credentials

    @property
    def livekit_enabled(self) -> bool:
        """Check if LiveKit is enabled and has valid credentials."""
        return self.livekit.enabled and self.livekit.has_credentials

    @property
    def livekit_url(self) -> str:
        """Get the LiveKit WebSocket URL for client connections."""
        return self.livekit.url

    @property
    def livekit_http_url(self) -> str:
        """Get the LiveKit HTTP URL for server-side API calls."""
        return self.livekit.http_url

    # ============================================================
    # Environment Override Extraction
    # ============================================================

    def _extract_graphiti_env_overrides(self) -> dict[str, Any]:
        """Extract Graphiti settings from environment variables and extras."""
        extras: dict[str, Any] = getattr(self, "model_extra", {}) or {}

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
            "graphiti_search_limit": ("search_limit", coerce_int),
            "graphiti_search_results_limit": ("search_limit", coerce_int),
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
            "ollama_embedding_dim": ("ollama_embedding_dim", coerce_int),
            "graphiti_ollama_embedding_dim": ("ollama_embedding_dim", coerce_int),
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

        return self._extract_env_overrides(extras, mapping)

    def _extract_mongo_env_overrides(self) -> dict[str, Any]:
        """Extract MongoDB settings from environment variables and extras."""
        extras: dict[str, Any] = getattr(self, "model_extra", {}) or {}

        mapping: dict[str, tuple[str, Callable[[Any], Any]]] = {
            "mongo_enabled": ("enabled", coerce_bool),
            "mongodb_enabled": ("enabled", coerce_bool),
            "mongo_uri": ("uri", coerce_str),
            "mongodb_uri": ("uri", coerce_str),
            "mongo_database": ("database", coerce_str),
            "mongodb_database": ("database", coerce_str),
            "mongo_policies_collection": ("policies_collection", coerce_str),
            "mongodb_policies_collection": ("policies_collection", coerce_str),
            "mongo_server_selection_timeout_ms": ("server_selection_timeout_ms", coerce_int),
            "mongodb_server_selection_timeout_ms": ("server_selection_timeout_ms", coerce_int),
        }

        return self._extract_env_overrides(extras, mapping)

    def _extract_livekit_env_overrides(self) -> dict[str, Any]:
        """Extract LiveKit settings from environment variables and extras."""
        extras: dict[str, Any] = getattr(self, "model_extra", {}) or {}

        mapping: dict[str, tuple[str, Callable[[Any], Any]]] = {
            # Core settings
            "livekit_enabled": ("enabled", coerce_bool),
            "livekit_url": ("url", coerce_str),
            "livekit_server_url": ("server_url", coerce_str),
            "livekit_api_key": ("api_key", coerce_str),
            "livekit_api_secret": ("api_secret", coerce_str),
            # AI Provider keys
            "livekit_gemini_api_key": ("gemini_api_key", coerce_str),
            "livekit_openai_api_key": ("openai_api_key", coerce_str),
            "livekit_deepgram_api_key": ("deepgram_api_key", coerce_str),
            "livekit_azure_api_key": ("azure_api_key", coerce_str),
            "livekit_azure_region": ("azure_region", coerce_str),
            # Model settings
            "livekit_deepgram_model": ("deepgram_model", coerce_str),
            "livekit_azure_tts_voice": ("azure_tts_voice", coerce_str),
            "livekit_openai_model": ("openai_model", coerce_str),
            "livekit_gemini_model": ("gemini_model", coerce_str),
            # Room settings
            "livekit_room_empty_timeout": ("room_empty_timeout", coerce_int),
            "livekit_room_max_participants": ("room_max_participants", coerce_int),
        }

        return self._extract_env_overrides(extras, mapping)

    def _extract_env_overrides(
        self,
        extras: dict[str, Any],
        mapping: dict[str, tuple[str, Callable[[Any], Any]]],
    ) -> dict[str, Any]:
        """Generic helper to extract env overrides based on a mapping."""
        overrides: dict[str, Any] = {}
        extras_lower = {
            (key or "").lower(): value 
            for key, value in extras.items() 
            if value is not None
        }
        
        # Load env file values
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
            # Priority: extras > os.environ > env file
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


# ============================================================
# Settings Factory & Cache
# ============================================================

_settings_cache: dict[str | None, Settings] = {}


def get_settings(
    app_name: str | None = None,
    override: Optional[dict] = None,
    *,
    force_reload: bool = False,
) -> Settings:
    """
    Get settings with optional app-specific .env override.
    
    Loading order (later values override earlier):
    1. apps/config/.env (shared base configuration)
    2. apps/{app_name}/.env (app-specific overrides)
    3. Environment variables (os.environ)
    4. Explicit overrides passed to this function
    
    Args:
        app_name: The app folder name (e.g., "ai", "voice") whose .env to load
        override: Explicit dict overrides to apply on top
        force_reload: If True, bypass cache and reload from env files
        
    Returns:
        Configured Settings instance
        
    Example:
        # In apps/ai/src/main.py
        settings = get_settings("ai")  # Loads apps/config/.env + apps/ai/.env
        
        # In apps/voice/agent.py  
        settings = get_settings("voice")  # Loads apps/config/.env + apps/voice/.env
    """
    cache_key = app_name if not override else None
    
    # Return cached if available and not forcing reload
    if not force_reload and cache_key and cache_key in _settings_cache and not override:
        return _settings_cache[cache_key]
    
    # Step 1: Load shared base config (apps/config/.env)
    if _ENV_FILE_PATH.exists():
        load_dotenv(_ENV_FILE_PATH, override=False)
    
    # Step 2: Load app-specific .env (apps/{app_name}/.env) - overrides base
    app_env_path = _get_app_env_path(app_name)
    if app_env_path:
        load_dotenv(app_env_path, override=True)
    
    # Step 3 & 4: Create settings (picks up env vars + explicit overrides)
    settings = Settings(**(override or {}))
    
    # Cache if no explicit overrides
    if cache_key:
        _settings_cache[cache_key] = settings
    
    return settings


def clear_settings_cache() -> None:
    """Clear the settings cache. Useful for testing."""
    _settings_cache.clear()
