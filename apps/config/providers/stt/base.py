"""Base STT provider with automatic subclass registration."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel


class BaseSTTProvider(BaseModel):
    """Abstract base for speech-to-text provider settings.

    Subclasses **must** define:
    * ``provider_name: ClassVar[str]``
    * ``provider: Literal["<name>"]``
    * ``from_vault(secrets)``
    * ``is_configured`` property
    """

    provider: str

    _registry: ClassVar[dict[str, type["BaseSTTProvider"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        name: str | None = getattr(cls, "provider_name", None)
        if name is not None:
            BaseSTTProvider._registry[name] = cls

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "BaseSTTProvider":
        raise NotImplementedError

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "BaseSTTProvider":
        raise NotImplementedError

    @property
    def is_configured(self) -> bool:
        raise NotImplementedError
