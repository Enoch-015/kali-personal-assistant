"""Factory for loading TTS provider settings via the registry."""

from __future__ import annotations

from typing import Any

from .base import BaseTTSProvider


def load_tts_provider(
    provider: str,
    secrets: dict[str, Any] | None = None,
    *,
    env: dict[str, Any] | None = None,
) -> BaseTTSProvider:
    """Resolve *provider* from the registry and hydrate from secrets or env."""
    cls = BaseTTSProvider._registry.get(provider)
    if cls is None:
        available = ", ".join(sorted(BaseTTSProvider._registry)) or "(none)"
        raise ValueError(f"Unknown TTS provider: {provider!r}. Available: {available}")

    if secrets is not None:
        return cls.from_vault(secrets)
    if env is not None:
        return cls.from_env(env)

    raise ValueError(f"Cannot load TTS provider {provider!r}: supply 'secrets' or 'env'.")


def get_available_tts_providers() -> list[str]:
    return sorted(BaseTTSProvider._registry)
