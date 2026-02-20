"""Deepgram STT provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseSTTProvider


class DeepgramSTTProvider(BaseSTTProvider):
    """Settings for Deepgram speech-to-text."""

    provider_name: ClassVar[str] = "deepgram"
    provider: Literal["deepgram"] = "deepgram"

    api_key: Optional[str] = Field(default=None, description="Deepgram API key.")
    model: str = Field(default="nova-2", description="Deepgram STT model.")

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "DeepgramSTTProvider":
        return cls(
            api_key=secrets.get("deepgram-api-key") or secrets.get("deepgram_api_key"),
            model=secrets.get("deepgram-model") or secrets.get("deepgram_model") or "nova-2",
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "DeepgramSTTProvider":
        return cls(
            api_key=env.get("deepgram_api_key") or env.get("DEEPGRAM_API_KEY") or env.get("LIVEKIT_DEEPGRAM_API_KEY"),
            model=env.get("deepgram_model") or env.get("LIVEKIT_DEEPGRAM_MODEL") or "nova-2",
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
