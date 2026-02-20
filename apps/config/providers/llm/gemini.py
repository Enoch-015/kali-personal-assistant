"""Google Gemini LLM provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """Settings for the Google Gemini API."""

    provider_name: ClassVar[str] = "gemini"
    provider: Literal["gemini"] = "gemini"

    api_key: Optional[str] = Field(default=None, description="Google / Gemini API key.")
    model: str = Field(default="gemini-2.0-flash", description="Primary Gemini model.")
    embedding_model: str = Field(default="embedding-001", description="Gemini embedding model.")
    reranker_model: str = Field(
        default="gemini-2.0-flash-exp", description="Model used for cross-encoding / reranking."
    )

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "GeminiProvider":
        return cls(
            api_key=secrets.get("google-api-key") or secrets.get("gemini-api-key") or secrets.get("google_api_key"),
            model=secrets.get("gemini-model") or secrets.get("gemini_model") or "gemini-2.0-flash",
            embedding_model=secrets.get("gemini-embedding-model") or secrets.get("gemini_embedding_model") or "embedding-001",
            reranker_model=secrets.get("gemini-reranker-model") or secrets.get("gemini_reranker_model") or "gemini-2.0-flash-exp",
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "GeminiProvider":
        return cls(
            api_key=env.get("gemini_api_key") or env.get("google_api_key") or env.get("GOOGLE_API_KEY"),
            model=env.get("gemini_model") or env.get("GEMINI_MODEL") or "gemini-2.0-flash",
            embedding_model=env.get("gemini_embedding_model") or env.get("GEMINI_EMBEDDING_MODEL") or "embedding-001",
            reranker_model=env.get("gemini_reranker_model") or env.get("GEMINI_RERANKER_MODEL") or "gemini-2.0-flash-exp",
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
