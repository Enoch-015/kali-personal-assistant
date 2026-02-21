"""Generic OpenAI-compatible LLM provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseLLMProvider


class GenericProvider(BaseLLMProvider):
    """Settings for any OpenAI-compatible endpoint (e.g. Mistral, vLLM)."""

    provider_name: ClassVar[str] = "generic"
    provider: Literal["generic"] = "generic"

    api_key: Optional[str] = Field(default=None, description="API key.")
    base_url: Optional[str] = Field(default=None, description="Base URL of the API.")
    model: str = Field(default="mistral-large-latest", description="Primary model.")
    small_model: str = Field(default="mistral-small-latest", description="Smaller model.")
    embedding_model: str = Field(default="mistral-embed", description="Embedding model.")

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "GenericProvider":
        return cls(
            api_key=secrets.get("generic-api-key") or secrets.get("generic_api_key"),
            base_url=secrets.get("generic-base-url") or secrets.get("generic_base_url"),
            model=secrets.get("generic-model") or secrets.get("generic_model") or "mistral-large-latest",
            small_model=secrets.get("generic-small-model") or secrets.get("generic_small_model") or "mistral-small-latest",
            embedding_model=secrets.get("generic-embedding-model") or secrets.get("generic_embedding_model") or "mistral-embed",
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "GenericProvider":
        return cls(
            api_key=env.get("generic_api_key") or env.get("GENERIC_API_KEY"),
            base_url=env.get("generic_base_url") or env.get("GENERIC_BASE_URL"),
            model=env.get("generic_model") or env.get("GENERIC_MODEL") or "mistral-large-latest",
            small_model=env.get("generic_small_model") or env.get("GENERIC_SMALL_MODEL") or "mistral-small-latest",
            embedding_model=env.get("generic_embedding_model") or env.get("GENERIC_EMBEDDING_MODEL") or "mistral-embed",
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url)
