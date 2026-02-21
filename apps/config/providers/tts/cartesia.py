"""Cartesia TTS provider settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseTTSProvider


class CartesiaTTSProvider(BaseTTSProvider):
    """Settings for Cartesia text-to-speech."""

    provider_name: ClassVar[str] = "cartesia"
    provider: Literal["cartesia"] = "cartesia"

    api_key: Optional[str] = Field(default=None, description="Cartesia API key.")
    model: str = Field(default="sonic-2", description="Cartesia TTS model.")
    voice: str = Field(
        default="f786b574-daa5-4673-aa0c-cbe3e8534c02",
        description="Cartesia voice ID.",
    )

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "CartesiaTTSProvider":
        return cls(
            api_key=(
                secrets.get("cartesia-api-key")
                or secrets.get("cartesia_api_key")
            ),
            model=(
                secrets.get("cartesia-model")
                or secrets.get("cartesia_model")
                or "sonic-2"
            ),
            voice=(
                secrets.get("cartesia-voice")
                or secrets.get("cartesia_voice")
                or "f786b574-daa5-4673-aa0c-cbe3e8534c02"
            ),
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "CartesiaTTSProvider":
        return cls(
            api_key=(
                env.get("cartesia_api_key")
                or env.get("CARTESIA_API_KEY")
                or env.get("LIVEKIT_CARTESIA_API_KEY")
            ),
            model=(
                env.get("cartesia_model")
                or env.get("CARTESIA_MODEL")
                or env.get("LIVEKIT_CARTESIA_MODEL")
                or "sonic-2"
            ),
            voice=(
                env.get("cartesia_voice")
                or env.get("CARTESIA_VOICE")
                or env.get("LIVEKIT_CARTESIA_VOICE")
                or "f786b574-daa5-4673-aa0c-cbe3e8534c02"
            ),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
