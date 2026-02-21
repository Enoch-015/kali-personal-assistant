"""
Vault-backed Settings Loader

All configuration (secrets **and** tuning knobs) is stored in Vault so the
Nuxt admin page can update them at runtime.

Architecture:
    - Each service container receives only VAULT_ADDR, VAULT_ROLE_ID, VAULT_SECRET_ID
    - On startup, the service authenticates to Vault and fetches all config
    - Individual ``ServiceSettings.from_vault(secrets)`` factories hydrate each
      subsystem; provider registries resolve the discriminated unions.

Usage::

    from config.vault_loader import load_settings_from_vault
    settings = await load_settings_from_vault("ai")
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

from .vault_settings import VaultClient, VaultSettings, get_vault_client

logger = logging.getLogger(__name__)


# Service type definitions
ServiceType = Literal["ai", "voice", "web"]

# Vault secret paths each service needs
SERVICE_SECRET_PATHS: dict[str, list[str]] = {
    "ai": ["python-ai", "shared", "databases"],
    "voice": ["livekit", "shared", "databases"],
    "web": ["nuxt", "shared", "databases", "python-ai", "livekit"],
}

SERVICE_NAME_PREFIXES: dict[str, str] = {
    "ai": "PYTHON_AI",
    "voice": "LIVEKIT",
    "web": "NUXT",
}


async def get_vault_client_for_service(service_type: ServiceType) -> VaultClient:
    """Get a Vault client configured for a specific service."""
    service_prefix = SERVICE_NAME_PREFIXES.get(service_type, "")
    settings = VaultSettings.from_env(service_name=service_prefix)
    return await get_vault_client(settings)


# ====================================================================
# Raw secret loaders (one per Vault path, with env fallback)
# ====================================================================

async def _load_secrets(
    client: VaultClient,
    getter: str,
    fallback: dict[str, str],
    *,
    label: str,
) -> dict[str, Any]:
    """Call *getter* on *client*; on failure fall back to env vars."""
    try:
        return await getattr(client, getter)()
    except Exception as e:
        logger.warning("Failed to load %s from Vault: %s. Using env fallback.", label, e)
        return {k: os.getenv(env_key, "") for k, env_key in fallback.items()}


async def load_database_secrets(client: VaultClient) -> dict[str, Any]:
    return await _load_secrets(
        client,
        "get_database_secrets",
        {
            "redis-url": "REDIS_URL",
            "neo4j-uri": "NEO4J_URI",
            "neo4j-username": "NEO4J_USERNAME",
            "neo4j-password": "NEO4J_PASSWORD",
            "mongodb-uri": "MONGODB_URI",
        },
        label="database",
    )


async def load_ai_secrets(client: VaultClient) -> dict[str, Any]:
    return await _load_secrets(
        client,
        "get_ai_secrets",
        {
            "openai-api-key": "OPENAI_API_KEY",
            "anthropic-api-key": "ANTHROPIC_API_KEY",
            "google-api-key": "GOOGLE_API_KEY",
        },
        label="AI",
    )


async def load_livekit_secrets(client: VaultClient) -> dict[str, Any]:
    return await _load_secrets(
        client,
        "get_livekit_secrets",
        {
            "api-key": "LIVEKIT_API_KEY",
            "api-secret": "LIVEKIT_API_SECRET",
        },
        label="LiveKit",
    )


async def load_shared_secrets(client: VaultClient) -> dict[str, Any]:
    return await _load_secrets(
        client,
        "get_shared_secrets",
        {
            "resend-api-key": "RESEND_API_KEY",
        },
        label="shared",
    )


# ====================================================================
# Vault → Settings composition
# ====================================================================

async def load_vault_settings_dict(service_type: ServiceType) -> dict[str, dict[str, Any]]:
    """Load all raw Vault dicts for a service.

    Returns a mapping of path label → secret dict, e.g.:
    ``{"databases": {...}, "python-ai": {...}, ...}``
    """
    client = await get_vault_client_for_service(service_type)
    result: dict[str, dict[str, Any]] = {}
    paths = SERVICE_SECRET_PATHS.get(service_type, [])

    if "databases" in paths:
        result["databases"] = await load_database_secrets(client)
    if "python-ai" in paths:
        result["python-ai"] = await load_ai_secrets(client)
    if "livekit" in paths:
        result["livekit"] = await load_livekit_secrets(client)
    if "shared" in paths:
        result["shared"] = await load_shared_secrets(client)

    logger.info(
        "Loaded Vault paths for service '%s': %s",
        service_type,
        list(result.keys()),
    )
    return result


async def load_settings_from_vault(service_type: ServiceType):
    """Build a complete ``Settings`` object from Vault.

    Each service setting is hydrated via its own ``from_vault(secrets)``
    factory.  Provider registries resolve discriminated unions (LLM, graph
    store, TTS, STT) based on ``preferred-*`` keys stored in Vault.
    """
    # Ensure provider registries are populated
    import config.providers as _providers  # noqa: F401

    from .services.graphiti import GraphitiSettings
    from .services.langgraph import LangGraphSettings
    from .services.livekit import LiveKitSettings
    from .services.mongo import MongoSettings
    from .services.redis import RedisSettings
    from .services.resend import ResendSettings
    from .settings import Settings

    vault = await load_vault_settings_dict(service_type)

    db_secrets = vault.get("databases", {})
    ai_secrets = vault.get("python-ai", {})
    lk_secrets = vault.get("livekit", {})
    shared_secrets = vault.get("shared", {})

    # ── Build service settings via from_vault factories ──────────────

    redis = RedisSettings.from_vault(db_secrets)
    mongo = MongoSettings.from_vault(db_secrets)
    langgraph = LangGraphSettings.from_vault(ai_secrets)
    resend = ResendSettings.from_vault(shared_secrets)

    graphiti = GraphitiSettings.from_vault(
        ai_secrets=ai_secrets,
        db_secrets=db_secrets,
    )

    livekit = LiveKitSettings.from_vault(livekit_secrets=lk_secrets)

    # ── Compose final Settings ───────────────────────────────────────

    return Settings(
        redis=redis,
        mongo=mongo,
        langgraph=langgraph,
        resend=resend,
        graphiti=graphiti,
        livekit=livekit,
    )


# ====================================================================
# Synchronous wrapper
# ====================================================================

def load_settings_from_vault_sync(service_type: ServiceType):
    """Synchronous wrapper for ``load_settings_from_vault``."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    load_settings_from_vault(service_type),
                )
                return future.result()
        else:
            return loop.run_until_complete(load_settings_from_vault(service_type))
    except RuntimeError:
        return asyncio.run(load_settings_from_vault(service_type))
