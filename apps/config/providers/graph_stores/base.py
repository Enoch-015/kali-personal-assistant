"""Base graph store with automatic subclass registration.

Every concrete graph store subclass registers itself into
``BaseGraphStore._registry`` via ``__init_subclass__``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel


class BaseGraphStore(BaseModel):
    """Abstract base for all graph database store settings.

    Subclasses **must** define:
    * ``provider_name: ClassVar[str]`` – unique key for registry lookups.
    * ``provider: Literal["<name>"]``  – Pydantic discriminator field.
    * ``from_vault(secrets)``          – factory that builds from Vault data.
    * ``is_configured``                – property checking credentials.
    """

    provider: str

    _registry: ClassVar[dict[str, type["BaseGraphStore"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        name: str | None = getattr(cls, "provider_name", None)
        if name is not None:
            BaseGraphStore._registry[name] = cls

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "BaseGraphStore":
        """Create an instance from a dict of Vault secrets."""
        raise NotImplementedError

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "BaseGraphStore":
        """Create an instance from environment variables / extras dict."""
        raise NotImplementedError

    @property
    def is_configured(self) -> bool:
        """Return ``True`` when all required credentials are present."""
        raise NotImplementedError
