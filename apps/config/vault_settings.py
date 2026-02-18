"""
Vault Client Configuration and Settings

This module provides a secure HashiCorp Vault client for Python services.
It supports AppRole authentication, secret caching, and automatic token renewal.

Usage:
    from config.vault_settings import VaultSettings, get_vault_client
    
    # Get singleton client
    client = get_vault_client()
    
    # Read a secret
    secrets = await client.get_secret("python-ai")
    api_key = secrets.get("openai-api-key")
    
    # Or use convenience functions
    secrets = await client.get_ai_secrets()
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Optional

import hvac
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VaultSettings(BaseModel):
    """Vault connection configuration."""

    addr: str = Field(
        default="http://127.0.0.1:8200",
        description="Vault server address. Default to localhost for local dev. Use http://vault-dev:8200 for Docker networking.",
    )
    role_id: str = Field(
        default="",
        description="AppRole Role ID for authentication.",
    )
    secret_id: str = Field(
        default="",
        description="AppRole Secret ID for authentication.",
    )
    mount_point: str = Field(
        default="secret",
        description="KV v2 secrets engine mount point.",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="How long to cache secrets (in seconds). Default: 5 minutes.",
    )
    token_refresh_buffer_seconds: int = Field(
        default=300,
        description="Refresh token this many seconds before expiry.",
    )

    @classmethod
    def from_env(cls, prefix: str = "") -> "VaultSettings":
        """
        Load settings from environment variables.
        
        Args:
            prefix: Optional prefix for env vars (e.g., "PYTHON_AI_" -> PYTHON_AI_VAULT_ROLE_ID)
        """
        p = f"{prefix}_" if prefix else ""
        return cls(
            addr=os.getenv(f"{p}VAULT_ADDR", os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")),
            role_id=os.getenv(f"{p}VAULT_ROLE_ID", ""),
            secret_id=os.getenv(f"{p}VAULT_SECRET_ID", ""),
            mount_point=os.getenv(f"{p}VAULT_MOUNT_POINT", "secret"),
            cache_ttl_seconds=int(os.getenv(f"{p}VAULT_CACHE_TTL", "300")),
        )


class CachedSecret:
    """A cached secret with expiration tracking."""

    def __init__(self, data: dict[str, Any], ttl_seconds: int):
        self.data = data
        self.expiry = time.time() + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expiry


class VaultClient:
    """
    READ-ONLY Vault client with AppRole authentication and caching.
    
    This client is intentionally READ-ONLY for security. Python services
    (AI, LiveKit) only consume secrets configured via the Nuxt admin UI.
    Write operations must go through the Nuxt admin API endpoints.
    
    Features:
    - AppRole authentication (secure, identity-based)
    - Automatic token renewal before expiry
    - Secret caching with configurable TTL
    - Thread-safe singleton pattern
    - Graceful fallback for development
    
    Security Model:
    - This client uses an AppRole with read-only permissions
    - Write operations will fail with "permission denied"
    - All secret management is done via the Nuxt admin UI
    """

    def __init__(self, settings: VaultSettings):
        self.settings = settings
        self._client: hvac.Client | None = None
        self._token: str | None = None
        self._token_expiry: float = 0
        self._cache: dict[str, CachedSecret] = {}
        self._lock = asyncio.Lock()
        self._authenticated = False

    async def _authenticate(self) -> None:
        """Authenticate with Vault using AppRole."""
        if not self.settings.role_id or not self.settings.secret_id:
            logger.warning(
                "Vault credentials not configured. "
                "Set VAULT_ROLE_ID and VAULT_SECRET_ID environment variables."
            )
            return

        try:
            # Create unauthenticated client
            client = hvac.Client(url=self.settings.addr)

            # Authenticate via AppRole
            result = client.auth.approle.login(
                role_id=self.settings.role_id,
                secret_id=self.settings.secret_id,
            )

            # Extract token info
            self._token = result["auth"]["client_token"]
            lease_duration = result["auth"]["lease_duration"]
            self._token_expiry = time.time() + lease_duration

            # Create authenticated client
            self._client = hvac.Client(
                url=self.settings.addr,
                token=self._token,
            )
            self._authenticated = True

            logger.info(
                "Vault authentication successful. Token expires in %d seconds.",
                lease_duration,
            )

        except hvac.exceptions.VaultError as e:
            logger.error("Vault authentication failed: %s", e)
            raise RuntimeError(f"Failed to authenticate with Vault: {e}") from e
        except Exception as e:
            logger.error("Unexpected error during Vault authentication: %s", e)
            raise

    async def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid, non-expired token."""
        async with self._lock:
            # Check if we need to (re)authenticate
            buffer = self.settings.token_refresh_buffer_seconds
            needs_auth = (
                not self._authenticated
                or self._client is None
                or time.time() > (self._token_expiry - buffer)
            )

            if needs_auth:
                await self._authenticate()

            return self._authenticated

    async def get_secret(self, path: str, use_cache: bool = True) -> dict[str, Any]:
        """
        Read a secret from Vault.
        
        Args:
            path: Secret path (e.g., 'python-ai', 'shared', 'databases')
            use_cache: Whether to use cached value if available
            
        Returns:
            Dictionary of secret key-value pairs
            
        Raises:
            RuntimeError: If Vault is not configured or read fails
        """
        # Check cache first
        if use_cache and path in self._cache:
            cached = self._cache[path]
            if not cached.is_expired:
                logger.debug("Returning cached secret for path: %s", path)
                return cached.data

        # Ensure we're authenticated
        if not await self._ensure_authenticated():
            raise RuntimeError(
                "Vault not configured. Set VAULT_ROLE_ID and VAULT_SECRET_ID."
            )

        try:
            # Read from Vault KV v2
            result = self._client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.settings.mount_point,
            )

            secret_data = result["data"]["data"]

            # Cache the result
            self._cache[path] = CachedSecret(
                data=secret_data,
                ttl_seconds=self.settings.cache_ttl_seconds,
            )

            logger.debug("Successfully read secret from path: %s", path)
            return secret_data

        except hvac.exceptions.InvalidPath:
            logger.warning("Secret path not found: %s", path)
            return {}
        except hvac.exceptions.Forbidden:
            logger.error("Access denied to secret path: %s", path)
            raise RuntimeError(f"Access denied to Vault path: {path}")
        except Exception as e:
            logger.error("Failed to read secret from %s: %s", path, e)
            raise RuntimeError(f"Failed to read secret: {e}") from e

    async def get_secret_key(self, path: str, key: str, default: Any = None) -> Any:
        """
        Get a specific key from a secret.
        
        Args:
            path: Secret path
            key: Key within the secret
            default: Default value if key not found
            
        Returns:
            The secret value or default
        """
        secrets = await self.get_secret(path)
        return secrets.get(key, default)

    def clear_cache(self, path: str | None = None) -> None:
        """
        Clear the secrets cache.
        
        Args:
            path: Specific path to clear, or None for all
        """
        if path:
            self._cache.pop(path, None)
            logger.debug("Cleared cache for path: %s", path)
        else:
            self._cache.clear()
            logger.debug("Cleared entire secrets cache")

    # ============================
    # Convenience Methods
    # ============================

    async def get_ai_secrets(self) -> dict[str, Any]:
        """Get secrets for the AI service."""
        return await self.get_secret("python-ai")

    async def get_livekit_secrets(self) -> dict[str, Any]:
        """Get secrets for the LiveKit voice service."""
        return await self.get_secret("livekit")

    async def get_shared_secrets(self) -> dict[str, Any]:
        """Get shared secrets (API keys, etc.)."""
        return await self.get_secret("shared")

    async def get_database_secrets(self) -> dict[str, Any]:
        """Get database connection secrets."""
        return await self.get_secret("databases")

    async def get_openai_api_key(self) -> str:
        """Get the OpenAI API key."""
        return await self.get_secret_key("python-ai", "openai-api-key", "")

    async def get_anthropic_api_key(self) -> str:
        """Get the Anthropic API key."""
        return await self.get_secret_key("python-ai", "anthropic-api-key", "")

    async def get_google_api_key(self) -> str:
        """Get the Google API key."""
        return await self.get_secret_key("python-ai", "google-api-key", "")

    async def get_resend_api_key(self) -> str:
        """Get the Resend email API key."""
        return await self.get_secret_key("shared", "resend-api-key", "")

    # ============================
    # Health Check
    # ============================

    async def health_check(self) -> dict[str, Any]:
        """
        Check Vault connectivity and authentication status.
        
        Returns:
            Health status dictionary
        """
        status = {
            "vault_addr": self.settings.addr,
            "authenticated": self._authenticated,
            "token_valid": False,
            "cache_size": len(self._cache),
        }

        try:
            if self._client:
                # Check if token is still valid
                status["token_valid"] = self._client.is_authenticated()

            # Try to read a test path
            await self._ensure_authenticated()
            status["connected"] = True
            status["authenticated"] = self._authenticated

        except Exception as e:
            status["connected"] = False
            status["error"] = str(e)

        return status


# ============================
# Singleton Instance
# ============================

_vault_client: VaultClient | None = None
_vault_lock = asyncio.Lock()


async def get_vault_client(settings: VaultSettings | None = None) -> VaultClient:
    """
    Get the singleton Vault client instance.
    
    Args:
        settings: Optional settings override. If not provided, loads from environment.
        
    Returns:
        Configured VaultClient instance
    """
    global _vault_client

    async with _vault_lock:
        if _vault_client is None:
            if settings is None:
                settings = VaultSettings.from_env()
            _vault_client = VaultClient(settings)

        return _vault_client


def get_vault_client_sync(settings: VaultSettings | None = None) -> VaultClient:
    """
    Get the singleton Vault client instance (synchronous version).
    
    For use in synchronous code that can't use async/await.
    """
    global _vault_client

    if _vault_client is None:
        if settings is None:
            settings = VaultSettings.from_env()
        _vault_client = VaultClient(settings)

    return _vault_client


def clear_vault_client() -> None:
    """Clear the singleton instance (useful for testing)."""
    global _vault_client
    _vault_client = None


# ============================
# Safe Logging Utility
# ============================

def safe_log_secrets(secrets: dict[str, Any], reveal_chars: int = 4) -> dict[str, str]:
    """
    Create a safe-to-log version of secrets dictionary.
    
    Args:
        secrets: Original secrets dict
        reveal_chars: Number of characters to show at start of value
        
    Returns:
        Dictionary with masked values
    """
    masked = {}
    for key, value in secrets.items():
        if value is None:
            masked[key] = "None"
        elif isinstance(value, str):
            if len(value) <= reveal_chars:
                masked[key] = "*" * len(value)
            else:
                masked[key] = value[:reveal_chars] + "*" * (len(value) - reveal_chars)
        else:
            masked[key] = f"<{type(value).__name__}>"
    return masked
