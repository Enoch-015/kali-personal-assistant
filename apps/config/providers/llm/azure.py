"""Azure OpenAI LLM provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseLLMProvider


class AzureOpenAIProvider(BaseLLMProvider):
    """Settings for Azure-hosted OpenAI deployments."""

    provider_name: ClassVar[str] = "azure"
    provider: Literal["azure"] = "azure"

    # LLM
    api_key: Optional[str] = Field(default=None, description="Azure OpenAI API key.")
    endpoint: Optional[str] = Field(default=None, description="Azure OpenAI endpoint URL.")
    deployment_name: Optional[str] = Field(default=None, description="Azure deployment name.")
    api_version: Optional[str] = Field(default=None, description="API version string.")

    # Embedding
    embedding_api_key: Optional[str] = Field(default=None, description="Embedding deployment key.")
    embedding_endpoint: Optional[str] = Field(default=None, description="Embedding endpoint URL.")
    embedding_deployment_name: Optional[str] = Field(default=None, description="Embedding deployment name.")
    embedding_api_version: Optional[str] = Field(default=None, description="Embedding API version.")

    # Auth
    use_managed_identity: Optional[bool] = Field(
        default=None, description="Use Azure Managed Identities for auth."
    )

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "AzureOpenAIProvider":
        return cls(
            api_key=secrets.get("openai-api-key") or secrets.get("azure-openai-api-key"),
            endpoint=secrets.get("azure-openai-endpoint"),
            deployment_name=secrets.get("azure-openai-deployment-name"),
            api_version=secrets.get("azure-openai-api-version"),
            embedding_api_key=secrets.get("azure-openai-embedding-api-key"),
            embedding_endpoint=secrets.get("azure-openai-embedding-endpoint"),
            embedding_deployment_name=secrets.get("azure-openai-embedding-deployment-name"),
            embedding_api_version=secrets.get("azure-openai-embedding-api-version"),
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "AzureOpenAIProvider":
        return cls(
            api_key=env.get("openai_api_key") or env.get("OPENAI_API_KEY"),
            endpoint=env.get("azure_openai_endpoint") or env.get("AZURE_OPENAI_ENDPOINT"),
            deployment_name=env.get("azure_openai_deployment_name") or env.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_version=env.get("azure_openai_api_version") or env.get("AZURE_OPENAI_API_VERSION"),
            embedding_api_key=env.get("azure_openai_embedding_api_key") or env.get("AZURE_OPENAI_EMBEDDING_API_KEY"),
            embedding_endpoint=env.get("azure_openai_embedding_endpoint") or env.get("AZURE_OPENAI_EMBEDDING_ENDPOINT"),
            embedding_deployment_name=env.get("azure_openai_embedding_deployment_name") or env.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
            embedding_api_version=env.get("azure_openai_embedding_api_version") or env.get("AZURE_OPENAI_EMBEDDING_API_VERSION"),
            use_managed_identity=_to_bool(env.get("azure_openai_use_managed_identity") or env.get("AZURE_OPENAI_USE_MANAGED_IDENTITY")),
        )

    @property
    def is_configured(self) -> bool:
        has_llm = bool(
            self.api_key
            and self.endpoint
            and self.deployment_name
            and self.api_version
        )
        has_embedder = bool(
            self.embedding_endpoint
            and self.embedding_deployment_name
            and self.embedding_api_version
            and (self.embedding_api_key or self.use_managed_identity)
        )
        return has_llm and has_embedder


def _to_bool(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "on"}
    return bool(val)
