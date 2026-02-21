"""Azure Speech TTS provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseTTSProvider


class AzureTTSProvider(BaseTTSProvider):
    """Settings for Azure Cognitive Services text-to-speech."""

    provider_name: ClassVar[str] = "azure"
    provider: Literal["azure"] = "azure"

    api_key: Optional[str] = Field(default=None, description="Azure Speech API key.")
    region: Optional[str] = Field(default=None, description="Azure Speech region (e.g. eastus).")
    voice: str = Field(default="en-NG-AbeoNeural", description="TTS voice identifier.")

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "AzureTTSProvider":
        return cls(
            api_key=secrets.get("azure-tts-api-key") or secrets.get("azure-speech-key") or secrets.get("azure_api_key"),
            region=secrets.get("azure-tts-region") or secrets.get("azure-speech-region") or secrets.get("azure_region"),
            voice=secrets.get("azure-tts-voice") or secrets.get("azure_tts_voice") or "en-NG-AbeoNeural",
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "AzureTTSProvider":
        return cls(
            api_key=env.get("azure_api_key") or env.get("AZURE_SPEECH_KEY") or env.get("LIVEKIT_AZURE_API_KEY"),
            region=env.get("azure_region") or env.get("AZURE_SPEECH_REGION") or env.get("LIVEKIT_AZURE_REGION"),
            voice=env.get("azure_tts_voice") or env.get("LIVEKIT_AZURE_TTS_VOICE") or "en-NG-AbeoNeural",
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.region)
