"""Base LLM provider with automatic subclass registration.

Every concrete provider subclass registers itself into ``BaseLLMProvider._registry``
via ``__init_subclass__``.  This means adding a new provider only requires creating
a new file – no existing code needs changing (Open/Closed Principle).
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel


class BaseLLMProvider(BaseModel):
    """Abstract base for all LLM provider settings.

    Subclasses **must** define:
    * ``provider_name: ClassVar[str]`` – unique key used for registry lookups.
    * ``provider: Literal["<name>"]``  – Pydantic discriminator field.
    * ``from_vault(secrets)``          – factory that builds the provider from Vault data.
    * ``is_configured``                – property that checks if all credentials are present.
    """

    provider: str

    # ---- registry --------------------------------------------------------
    _registry: ClassVar[dict[str, type["BaseLLMProvider"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        name: str | None = getattr(cls, "provider_name", None)
        if name is not None:
            BaseLLMProvider._registry[name] = cls

    # ---- abstract interface ----------------------------------------------
    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "BaseLLMProvider":
        """Create an instance from a dict of Vault secrets."""
        raise NotImplementedError

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "BaseLLMProvider":
        """Create an instance from environment variables / extras dict."""
        raise NotImplementedError

    @property
    def is_configured(self) -> bool:
        """Return ``True`` when all required credentials are present."""
        raise NotImplementedError

    @property
    def supports_vision(self) -> bool:
        """Return ``True`` if the configured model supports multimodal (vision) input."""
        return False
