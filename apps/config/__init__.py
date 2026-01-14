"""
Kali Personal Assistant - Configuration Package

Provides unified configuration for all Kali apps with per-app .env overrides.

Usage:
    from config import get_settings
    settings = get_settings("ai")  # or "voice", "web", etc.
"""

from .settings import (
    Settings,
    RedisSettings,
    MongoSettings,
    ResendSettings,
    LangGraphSettings,
    GraphitiSettings,
    get_settings,
    clear_settings_cache,
)

__all__ = [
    "Settings",
    "RedisSettings",
    "MongoSettings",
    "ResendSettings",
    "LangGraphSettings",
    "GraphitiSettings",
    "get_settings",
    "clear_settings_cache",
]
