"""Groq LLM provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    """Settings for the Groq API.

    Groq also requires an OpenAI key for embeddings.
    """

    provider_name: ClassVar[str] = "groq"
    provider: Literal["groq"] = "groq"

    api_key: Optional[str] = Field(default=None, description="Groq API key.")
    model: str = Field(default="llama-3.1-70b-versatile", description="Primary model.")
    small_model: str = Field(default="llama-3.1-8b-instant", description="Smaller model.")
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI key for embeddings (Groq has no native embedding model).",
    )

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "GroqProvider":
        return cls(
            api_key=secrets.get("groq-api-key") or secrets.get("groq_api_key"),
            model=secrets.get("groq-model") or secrets.get("groq_model") or "llama-3.1-70b-versatile",
            small_model=secrets.get("groq-small-model") or secrets.get("groq_small_model") or "llama-3.1-8b-instant",
            openai_api_key=secrets.get("openai-api-key") or secrets.get("openai_api_key"),
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "GroqProvider":
        return cls(
            api_key=env.get("groq_api_key") or env.get("GROQ_API_KEY"),
            model=env.get("groq_model") or env.get("GROQ_MODEL") or "llama-3.1-70b-versatile",
            small_model=env.get("groq_small_model") or env.get("GROQ_SMALL_MODEL") or "llama-3.1-8b-instant",
            openai_api_key=env.get("openai_api_key") or env.get("OPENAI_API_KEY"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.openai_api_key)
