"""
Kali Personal Assistant - Configuration Package

Provides unified configuration for all Kali apps with per-app .env overrides.

Usage:
    from config import get_settings
    settings = get_settings("ai")  # or "voice", "web", etc.
    
    # For Vault secrets (async)
    from config import get_vault_client, VaultSettings
    client = await get_vault_client()
    secrets = await client.get_ai_secrets()
    
    # Load settings from Vault (recommended for production)
    from config import load_settings_from_vault
    settings = await load_settings_from_vault("ai")  # or "voice", "web"
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

from .vault_loader import (
    load_settings_from_vault,
    load_settings_from_vault_sync,
    load_vault_settings_dict,
    get_vault_client_for_service,
    ServiceType,
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
    # Vault Loader (production settings from Vault)
    "load_settings_from_vault",
    "load_settings_from_vault_sync",
    "load_vault_settings_dict",
    "get_vault_client_for_service",
    "ServiceType",
]
