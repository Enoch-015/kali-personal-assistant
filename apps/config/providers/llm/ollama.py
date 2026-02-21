"""Ollama (local) LLM provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """Settings for a local Ollama instance."""

    provider_name: ClassVar[str] = "ollama"
    provider: Literal["ollama"] = "ollama"

    base_url: Optional[str] = Field(
        default="http://localhost:11434/v1", description="Ollama base URL."
    )
    model: str = Field(default="deepseek-r1:7b", description="LLM model name.")
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding model name.")
    embedding_dim: int = Field(default=768, description="Embedding vector dimension.")

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "OllamaProvider":
        return cls(
            base_url=secrets.get("ollama-base-url") or secrets.get("ollama_base_url") or "http://localhost:11434/v1",
            model=secrets.get("ollama-model") or secrets.get("ollama_model") or "deepseek-r1:7b",
            embedding_model=secrets.get("ollama-embedding-model") or secrets.get("ollama_embedding_model") or "nomic-embed-text",
            embedding_dim=int(secrets.get("ollama-embedding-dim") or secrets.get("ollama_embedding_dim") or 768),
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "OllamaProvider":
        return cls(
            base_url=env.get("ollama_base_url") or env.get("OLLAMA_BASE_URL") or "http://localhost:11434/v1",
            model=env.get("ollama_model") or env.get("OLLAMA_MODEL") or "deepseek-r1:7b",
            embedding_model=env.get("ollama_embedding_model") or env.get("OLLAMA_EMBEDDING_MODEL") or "nomic-embed-text",
            embedding_dim=int(env.get("ollama_embedding_dim") or env.get("OLLAMA_EMBEDDING_DIM") or 768),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.model and self.embedding_model)
