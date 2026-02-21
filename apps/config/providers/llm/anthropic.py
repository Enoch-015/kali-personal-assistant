"""Anthropic LLM provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Settings for the Anthropic API.

    Note: Anthropic also requires an OpenAI API key for embeddings
    (Anthropic does not offer its own embedding model).
    """

    provider_name: ClassVar[str] = "anthropic"
    provider: Literal["anthropic"] = "anthropic"

    api_key: Optional[str] = Field(default=None, description="Anthropic API key.")
    model: str = Field(default="claude-sonnet-4-20250514", description="Primary model.")
    small_model: str = Field(default="claude-3-5-haiku-20241022", description="Smaller / faster model.")
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI key for embeddings (Anthropic has no native embedding model).",
    )

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "AnthropicProvider":
        return cls(
            api_key=secrets.get("anthropic-api-key") or secrets.get("anthropic_api_key"),
            model=secrets.get("anthropic-model") or secrets.get("anthropic_model") or "claude-sonnet-4-20250514",
            small_model=secrets.get("anthropic-small-model") or secrets.get("anthropic_small_model") or "claude-3-5-haiku-20241022",
            openai_api_key=secrets.get("openai-api-key") or secrets.get("openai_api_key"),
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "AnthropicProvider":
        return cls(
            api_key=env.get("anthropic_api_key") or env.get("ANTHROPIC_API_KEY"),
            model=env.get("anthropic_model") or env.get("ANTHROPIC_MODEL") or "claude-sonnet-4-20250514",
            small_model=env.get("anthropic_small_model") or env.get("ANTHROPIC_SMALL_MODEL") or "claude-3-5-haiku-20241022",
            openai_api_key=env.get("openai_api_key") or env.get("OPENAI_API_KEY"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.openai_api_key)
