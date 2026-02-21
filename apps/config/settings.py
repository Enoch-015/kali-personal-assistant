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

# Import from the new service-settings package
from .services.graphiti import GraphitiSettings
from .services.langgraph import LangGraphSettings
from .services.livekit import LiveKitSettings
from .services.mongo import MongoSettings
from .services.redis import RedisSettings
from .services.resend import ResendSettings

# Ensure the provider registry is populated on first import
import config.providers as _providers  # noqa: F401

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
        """Post-validation hook to wire up integrations from env overrides.

        When running locally (no Vault), env vars / .env are merged and
        passed through each service's ``from_env`` factory so provider
        registries can resolve the discriminated unions.
        """
        extras: dict[str, Any] = getattr(self, "model_extra", {}) or {}
        merged = self._build_merged_env(extras)

        # ---- Graphiti (provider-based + graph store) ----
        self._apply_graphiti_overrides(merged)

        # ---- LiveKit (provider-based: LLM/TTS/STT) ----
        self._apply_livekit_overrides(merged)

        # ---- MongoDB ----
        mongo_updates = self._extract_env_overrides(
            extras,
            {
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
            },
        )
        if mongo_updates:
            self.mongo = self.mongo.model_copy(update=mongo_updates)

        # ---- Redis ----
        redis_update: dict[str, Any] | None = None
        if self.redis_url_override:
            redis_update = {"url": self.redis_url_override}
        elif self.environment == "production":
            redis_update = {"url": self.redis.url}
        if redis_update:
            self.redis = self.redis.model_copy(update=redis_update)

        # ---- Resend ----
        if not self.resend.api_key and self.resend.deliver:
            self.resend = self.resend.model_copy(update={"deliver": False})

        return self

    # ------------------------------------------------------------------
    # Graphiti: delegate to the provider-based factory
    # ------------------------------------------------------------------

    def _apply_graphiti_overrides(self, merged: dict[str, Any]) -> None:
        """Build / update ``self.graphiti`` from env using the provider registry."""
        provider = (
            merged.get("graphiti_llm_provider")
            or merged.get("graphiti_provider")
            or merged.get("llm_provider")
        )
        graph_store = merged.get("graphiti_graph_store") or merged.get("graph_store")

        if provider or graph_store or any(
            k.startswith(("graphiti_", "neo4j_")) for k in merged
        ):
            new_graphiti = GraphitiSettings.from_env(
                merged, provider=provider, graph_store=graph_store,
            )
            updates: dict[str, Any] = {}
            for field_name in GraphitiSettings.model_fields:
                new_val = getattr(new_graphiti, field_name)
                old_val = getattr(self.graphiti, field_name)
                if new_val is not None and new_val != old_val:
                    updates[field_name] = new_val
            if updates:
                self.graphiti = self.graphiti.model_copy(update=updates)

        # Auto-enable/disable based on credentials
        if self.graphiti.has_credentials and not self.graphiti.enabled:
            self.graphiti = self.graphiti.model_copy(update={"enabled": True})
        if self.graphiti.enabled and not self.graphiti.has_credentials:
            self.graphiti = self.graphiti.model_copy(update={"enabled": False})

    # ------------------------------------------------------------------
    # LiveKit: delegate to the provider-based factory
    # ------------------------------------------------------------------

    def _apply_livekit_overrides(self, merged: dict[str, Any]) -> None:
        """Build / update ``self.livekit`` from env using the provider registries."""
        if any(k.startswith("livekit_") for k in merged):
            new_livekit = LiveKitSettings.from_env(merged)
            updates: dict[str, Any] = {}
            for field_name in LiveKitSettings.model_fields:
                new_val = getattr(new_livekit, field_name)
                old_val = getattr(self.livekit, field_name)
                if new_val is not None and new_val != old_val:
                    updates[field_name] = new_val
            if updates:
                self.livekit = self.livekit.model_copy(update=updates)

        if self.livekit.enabled and not self.livekit.has_credentials:
            self.livekit = self.livekit.model_copy(update={"enabled": False})

    def _build_merged_env(self, extras: dict[str, Any]) -> dict[str, Any]:
        """Priority: extras > os.environ > .env file.  All keys lower-cased."""
        merged: dict[str, Any] = {}
        if _ENV_FILE_PATH.exists():
            try:
                for k, v in (dotenv_values(_ENV_FILE_PATH) or {}).items():
                    if k and v is not None:
                        merged[k.lower()] = v
            except Exception:
                pass
        for k, v in os.environ.items():
            merged[k.lower()] = v
        for k, v in extras.items():
            if k and v is not None:
                merged[k.lower()] = v
        return merged

    # ------------------------------------------------------------------
    # Convenience Properties
    # ------------------------------------------------------------------

    @property
    def redis_url(self) -> RedisDsn:
        return self.redis.url

    @property
    def graphiti_enabled(self) -> bool:
        return self.graphiti.enabled and self.graphiti.has_credentials

    @property
    def livekit_enabled(self) -> bool:
        return self.livekit.enabled and self.livekit.has_credentials

    @property
    def livekit_url(self) -> str:
        return self.livekit.url

    @property
    def livekit_http_url(self) -> str:
        return self.livekit.http_url

    # ------------------------------------------------------------------
    # Generic env-override helper (used for Mongo, LiveKit, etc.)
    # ------------------------------------------------------------------

    def _extract_env_overrides(
        self,
        extras: dict[str, Any],
        mapping: dict[str, tuple[str, Callable[[Any], Any]]],
    ) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        extras_lower = {
            (key or "").lower(): value
            for key, value in extras.items()
            if value is not None
        }

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
    """
    cache_key = app_name if not override else None

    if not force_reload and cache_key and cache_key in _settings_cache and not override:
        return _settings_cache[cache_key]

    # Step 1: Load shared base config
    if _ENV_FILE_PATH.exists():
        load_dotenv(_ENV_FILE_PATH, override=False)

    # Step 2: Load app-specific .env
    app_env_path = _get_app_env_path(app_name)
    if app_env_path:
        load_dotenv(app_env_path, override=True)

    # Step 3 & 4: Create settings
    settings = Settings(**(override or {}))

    if cache_key:
        _settings_cache[cache_key] = settings

    return settings


def clear_settings_cache() -> None:
    """Clear the settings cache. Useful for testing."""
    _settings_cache.clear()
