"""Factory for loading graph store settings via the registry."""

from __future__ import annotations

from typing import Any

from .base import BaseGraphStore


def load_graph_store(
    provider: str,
    secrets: dict[str, Any] | None = None,
    *,
    env: dict[str, Any] | None = None,
) -> BaseGraphStore:
    """Resolve *provider* from the registry and hydrate from secrets or env."""
    cls = BaseGraphStore._registry.get(provider)
    if cls is None:
        available = ", ".join(sorted(BaseGraphStore._registry)) or "(none)"
        raise ValueError(f"Unknown graph store: {provider!r}. Available: {available}")

    if secrets is not None:
        return cls.from_vault(secrets)
    if env is not None:
        return cls.from_env(env)

    raise ValueError(f"Cannot load graph store {provider!r}: supply 'secrets' or 'env'.")


def get_available_graph_stores() -> list[str]:
    """Return sorted list of registered graph store names."""
    return sorted(BaseGraphStore._registry)
