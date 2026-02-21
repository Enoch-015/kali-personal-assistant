"""Factory for loading LLM provider settings via the registry."""

from __future__ import annotations

from typing import Any

from .base import BaseLLMProvider


def load_llm_provider(
    provider: str,
    secrets: dict[str, Any] | None = None,
    *,
    env: dict[str, Any] | None = None,
) -> BaseLLMProvider:
    """Resolve *provider* from the registry and hydrate from secrets or env.

    Parameters
    ----------
    provider:
        Provider key (e.g. ``"openai"``, ``"gemini"``).
    secrets:
        Vault-sourced dict – passed to ``cls.from_vault()``.
    env:
        Environment / extras dict – passed to ``cls.from_env()``.

    Returns
    -------
    BaseLLMProvider
        Fully-hydrated provider settings.

    Raises
    ------
    ValueError
        If *provider* is not in the registry or no data source is given.
    """
    cls = BaseLLMProvider._registry.get(provider)
    if cls is None:
        available = ", ".join(sorted(BaseLLMProvider._registry)) or "(none)"
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. Available: {available}"
        )

    if secrets is not None:
        return cls.from_vault(secrets)
    if env is not None:
        return cls.from_env(env)

    raise ValueError(
        f"Cannot load provider {provider!r}: supply either 'secrets' (Vault) or 'env'."
    )


def get_available_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    return sorted(BaseLLMProvider._registry)
