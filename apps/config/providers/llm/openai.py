"""OpenAI LLM provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """Settings for the OpenAI API."""

    provider_name: ClassVar[str] = "openai"
    provider: Literal["openai"] = "openai"

    api_key: Optional[str] = Field(default=None, description="OpenAI API key.")
    model: str = Field(default="gpt-4o", description="Primary model name.")
    small_model: str = Field(default="gpt-3.5-turbo", description="Smaller / faster model.")
    embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model name."
    )

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "OpenAIProvider":
        return cls(
            api_key=secrets.get("openai-api-key") or secrets.get("openai_api_key"),
            model=secrets.get("openai-model") or secrets.get("openai_model") or "gpt-4o",
            small_model=secrets.get("openai-small-model") or secrets.get("openai_small_model") or "gpt-3.5-turbo",
            embedding_model=secrets.get("openai-embedding-model") or secrets.get("openai_embedding_model") or "text-embedding-3-small",
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "OpenAIProvider":
        return cls(
            api_key=env.get("openai_api_key") or env.get("OPENAI_API_KEY"),
            model=env.get("openai_model") or env.get("OPENAI_MODEL") or "gpt-4o",
            small_model=env.get("openai_small_model") or env.get("OPENAI_SMALL_MODEL") or "gpt-3.5-turbo",
            embedding_model=env.get("openai_embedding_model") or env.get("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small",
        )

    # Models known to support vision / multimodal input
    _VISION_MODELS: ClassVar[set[str]] = {
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-vision-preview",
        "o1", "o1-mini", "o3", "o3-mini", "o4-mini",
    }

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def supports_vision(self) -> bool:
        """Check if the configured model supports vision input."""
        model_lower = self.model.lower()
        # Exact match or prefix match (e.g. "gpt-4o-2024-05-13")
        return any(model_lower == v or model_lower.startswith(f"{v}-") for v in self._VISION_MODELS)
