"""Factory for loading STT provider settings via the registry."""

from __future__ import annotations

from typing import Any

from .base import BaseSTTProvider


def load_stt_provider(
    provider: str,
    secrets: dict[str, Any] | None = None,
    *,
    env: dict[str, Any] | None = None,
) -> BaseSTTProvider:
    """Resolve *provider* from the registry and hydrate from secrets or env."""
    cls = BaseSTTProvider._registry.get(provider)
    if cls is None:
        available = ", ".join(sorted(BaseSTTProvider._registry)) or "(none)"
        raise ValueError(f"Unknown STT provider: {provider!r}. Available: {available}")

    if secrets is not None:
        return cls.from_vault(secrets)
    if env is not None:
        return cls.from_env(env)

    raise ValueError(f"Cannot load STT provider {provider!r}: supply 'secrets' or 'env'.")


def get_available_stt_providers() -> list[str]:
    return sorted(BaseSTTProvider._registry)
