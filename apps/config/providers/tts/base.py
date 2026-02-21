"""Base TTS provider with automatic subclass registration."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel


class BaseTTSProvider(BaseModel):
    """Abstract base for text-to-speech provider settings.

    Subclasses **must** define:
    * ``provider_name: ClassVar[str]``
    * ``provider: Literal["<name>"]``
    * ``from_vault(secrets)``
    * ``is_configured`` property
    """

    provider: str

    _registry: ClassVar[dict[str, type["BaseTTSProvider"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        name: str | None = getattr(cls, "provider_name", None)
        if name is not None:
            BaseTTSProvider._registry[name] = cls

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "BaseTTSProvider":
        raise NotImplementedError

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "BaseTTSProvider":
        raise NotImplementedError

    @property
    def is_configured(self) -> bool:
        raise NotImplementedError
