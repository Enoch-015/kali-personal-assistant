"""
Kali Personal Assistant - Configuration Package

Provides unified configuration for all Kali apps with per-app .env overrides.

Usage:
    from config import get_settings
    settings = get_settings("ai")  # or "voice", "web", etc.
    
    # For Vault secrets
    from config import get_vault_client, VaultSettings
    client = await get_vault_client()
    secrets = await client.get_ai_secrets()
"""

from .settings import (
    Settings,
    RedisSettings,
    MongoSettings,
    ResendSettings,
    LangGraphSettings,
    GraphitiSettings,
    LiveKitSettings,
    get_settings,
    clear_settings_cache,
)

from .vault_settings import (
    VaultSettings,
    VaultClient,
    get_vault_client,
    get_vault_client_sync,
    clear_vault_client,
    safe_log_secrets,
)

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
    # Vault
    "VaultSettings",
    "VaultClient",
    "get_vault_client",
    "get_vault_client_sync",
    "clear_vault_client",
    "safe_log_secrets",
]
