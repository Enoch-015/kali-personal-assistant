"""
Vault-backed Settings Loader

This module provides functions to load application settings from Vault.
All sensitive configuration (database URIs, API keys) are fetched from Vault
rather than environment variables.

Architecture:
    - Each service container receives only VAULT_ADDR, VAULT_ROLE_ID, VAULT_SECRET_ID
    - On startup, the service authenticates to Vault and fetches all other config
    - This ensures secrets are never stored in env files or Docker images

Usage:
    from config.vault_loader import load_settings_from_vault
    
    # In apps/ai startup
    settings = await load_settings_from_vault("ai")
    
    # In apps/voice startup  
    settings = await load_settings_from_vault("voice")
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

from .vault_settings import VaultSettings, get_vault_client, VaultClient

logger = logging.getLogger(__name__)


# Service type definitions
ServiceType = Literal["ai", "voice", "web"]

# Mapping of service types to their Vault secret paths
SERVICE_SECRET_PATHS = {
    "ai": ["python-ai", "shared", "databases"],
    "voice": ["livekit", "shared", "databases"],
    "web": ["nuxt", "shared", "databases", "python-ai", "livekit"],  # Admin has access to all
}

# Mapping of service types to their VaultSettings service_name for local dev fallback
SERVICE_NAME_PREFIXES = {
    "ai": "PYTHON_AI",
    "voice": "LIVEKIT",
    "web": "NUXT",
}


async def get_vault_client_for_service(service_type: ServiceType) -> VaultClient:
    """
    Get a Vault client configured for a specific service.
    
    Args:
        service_type: The service type ("ai", "voice", "web")
        
    Returns:
        Configured VaultClient instance
    """
    # Get the service name prefix for local dev fallback
    service_prefix = SERVICE_NAME_PREFIXES.get(service_type, "")
    
    # Create settings with appropriate fallback for local dev
    settings = VaultSettings.from_env(service_name=service_prefix)
    
    return await get_vault_client(settings)


async def load_database_settings(client: VaultClient) -> dict[str, Any]:
    """
    Load database connection settings from Vault.
    
    Returns dict with keys:
        - redis_url
        - neo4j_uri, neo4j_username, neo4j_password
        - mongodb_uri
    """
    try:
        secrets = await client.get_database_secrets()
        return {
            "redis_url": secrets.get("redis-url", "redis://localhost:6379/0"),
            "neo4j_uri": secrets.get("neo4j-uri", "bolt://localhost:7687"),
            "neo4j_username": secrets.get("neo4j-username", "neo4j"),
            "neo4j_password": secrets.get("neo4j-password", "password"),
            "mongodb_uri": secrets.get("mongodb-uri", "mongodb://localhost:27017"),
        }
    except Exception as e:
        logger.warning("Failed to load database secrets from Vault: %s. Using defaults.", e)
        return {
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "neo4j_username": os.getenv("NEO4J_USERNAME", "neo4j"),
            "neo4j_password": os.getenv("NEO4J_PASSWORD", "password"),
            "mongodb_uri": os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        }


async def load_ai_settings(client: VaultClient) -> dict[str, Any]:
    """
    Load AI service settings from Vault.
    
    Returns dict with keys:
        - openai_api_key
        - anthropic_api_key
        - google_api_key (for Gemini)
    """
    try:
        secrets = await client.get_ai_secrets()
        return {
            "openai_api_key": secrets.get("openai-api-key", ""),
            "anthropic_api_key": secrets.get("anthropic-api-key", ""),
            "google_api_key": secrets.get("google-api-key", ""),
        }
    except Exception as e:
        logger.warning("Failed to load AI secrets from Vault: %s", e)
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            "google_api_key": os.getenv("GOOGLE_API_KEY", ""),
        }


async def load_livekit_settings(client: VaultClient) -> dict[str, Any]:
    """
    Load LiveKit settings from Vault.
    
    Returns dict with keys:
        - livekit_api_key
        - livekit_api_secret
    """
    try:
        secrets = await client.get_livekit_secrets()
        return {
            "livekit_api_key": secrets.get("api-key", "devkey"),
            "livekit_api_secret": secrets.get("api-secret", "secret"),
        }
    except Exception as e:
        logger.warning("Failed to load LiveKit secrets from Vault: %s", e)
        return {
            "livekit_api_key": os.getenv("LIVEKIT_API_KEY", "devkey"),
            "livekit_api_secret": os.getenv("LIVEKIT_API_SECRET", "secret"),
        }


async def load_shared_settings(client: VaultClient) -> dict[str, Any]:
    """
    Load shared settings from Vault.
    
    Returns dict with keys:
        - resend_api_key
    """
    try:
        secrets = await client.get_shared_secrets()
        return {
            "resend_api_key": secrets.get("resend-api-key", ""),
        }
    except Exception as e:
        logger.warning("Failed to load shared secrets from Vault: %s", e)
        return {
            "resend_api_key": os.getenv("RESEND_API_KEY", ""),
        }


async def load_vault_settings_dict(service_type: ServiceType) -> dict[str, Any]:
    """
    Load all settings for a service from Vault.
    
    This is the main entry point for services to get their configuration.
    It fetches all secrets the service needs and returns them as a dict
    that can be used to configure pydantic Settings.
    
    Args:
        service_type: The service type ("ai", "voice", "web")
        
    Returns:
        Dictionary of settings loaded from Vault
    """
    client = await get_vault_client_for_service(service_type)
    
    # Start with database settings (needed by all services)
    settings: dict[str, Any] = {}
    
    # Load based on service type
    paths = SERVICE_SECRET_PATHS.get(service_type, [])
    
    if "databases" in paths:
        db_settings = await load_database_settings(client)
        settings.update(db_settings)
    
    if "python-ai" in paths:
        ai_settings = await load_ai_settings(client)
        settings.update(ai_settings)
    
    if "livekit" in paths:
        lk_settings = await load_livekit_settings(client)
        settings.update(lk_settings)
    
    if "shared" in paths:
        shared_settings = await load_shared_settings(client)
        settings.update(shared_settings)
    
    logger.info(
        "Loaded settings from Vault for service '%s'. Keys: %s",
        service_type,
        list(settings.keys()),
    )
    
    return settings


async def load_settings_from_vault(service_type: ServiceType):
    """
    Load complete Settings object with values from Vault.
    
    This creates a Settings instance with all configuration loaded from Vault.
    Use this as the primary way to get settings in production.
    
    Args:
        service_type: The service type ("ai", "voice", "web")
        
    Returns:
        Configured Settings instance
        
    Example:
        # In apps/ai/src/main.py
        settings = await load_settings_from_vault("ai")
        redis_url = settings.redis_url
        api_key = settings.graphiti.openai_api_key
    """
    # Import here to avoid circular imports
    from .settings import Settings
    
    # Load settings from Vault
    vault_settings = await load_vault_settings_dict(service_type)
    
    # Map Vault settings to Settings fields
    overrides: dict[str, Any] = {}
    
    # Redis
    if "redis_url" in vault_settings:
        overrides["redis_url_override"] = vault_settings["redis_url"]
    
    # MongoDB (via model_extra for extraction)
    if "mongodb_uri" in vault_settings:
        overrides["mongodb_uri"] = vault_settings["mongodb_uri"]
    
    # Neo4j/Graphiti
    if "neo4j_uri" in vault_settings:
        overrides["neo4j_uri"] = vault_settings["neo4j_uri"]
        overrides["neo4j_user"] = vault_settings.get("neo4j_username", "neo4j")
        overrides["neo4j_password"] = vault_settings.get("neo4j_password", "")
    
    # API Keys
    if "openai_api_key" in vault_settings:
        overrides["openai_api_key"] = vault_settings["openai_api_key"]
    if "anthropic_api_key" in vault_settings:
        overrides["anthropic_api_key"] = vault_settings["anthropic_api_key"]
    if "google_api_key" in vault_settings:
        overrides["google_api_key"] = vault_settings["google_api_key"]
    
    # LiveKit
    if "livekit_api_key" in vault_settings:
        overrides["livekit_api_key"] = vault_settings["livekit_api_key"]
        overrides["livekit_api_secret"] = vault_settings.get("livekit_api_secret", "")
    
    # Resend
    if "resend_api_key" in vault_settings:
        overrides["resend_api_key"] = vault_settings["resend_api_key"]
    
    # Create Settings with Vault-loaded values
    return Settings(**overrides)


# Synchronous wrapper for use in non-async contexts
def load_settings_from_vault_sync(service_type: ServiceType):
    """
    Synchronous wrapper for load_settings_from_vault.
    
    For use in contexts where async isn't available (e.g., module-level imports).
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we need to use a different approach
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    load_settings_from_vault(service_type)
                )
                return future.result()
        else:
            return loop.run_until_complete(load_settings_from_vault(service_type))
    except RuntimeError:
        # No event loop exists
        return asyncio.run(load_settings_from_vault(service_type))
