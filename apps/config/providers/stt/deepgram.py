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
    language: str = Field(default="en", description="Language code (e.g. 'en', 'multi' for multilingual).")

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "DeepgramSTTProvider":
        return cls(
            api_key=secrets.get("deepgram-api-key") or secrets.get("deepgram_api_key"),
            model=secrets.get("deepgram-model") or secrets.get("deepgram_model") or "nova-2",
            language=secrets.get("deepgram-language") or secrets.get("deepgram_language") or "en",
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "DeepgramSTTProvider":
        return cls(
            api_key=env.get("deepgram_api_key") or env.get("DEEPGRAM_API_KEY") or env.get("LIVEKIT_DEEPGRAM_API_KEY"),
            model=env.get("deepgram_model") or env.get("LIVEKIT_DEEPGRAM_MODEL") or "nova-2",
            language=env.get("deepgram_language") or env.get("LIVEKIT_DEEPGRAM_LANGUAGE") or "en",
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
