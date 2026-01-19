"""LiveKit configuration settings for real-time video/audio communication."""

from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, computed_field


class LiveKitSettings(BaseModel):
    """LiveKit configuration settings model."""

    model_config = ConfigDict(populate_by_name=True)

    # Core LiveKit Server Settings
    enabled: bool = Field(
        default=True,
        description="Whether LiveKit integration is enabled.",
        validation_alias=AliasChoices("LIVEKIT_ENABLED", "livekit_enabled"),
    )
    url: str = Field(
        default="ws://localhost:7880",
        description="The WebSocket URL of the LiveKit server (for client connections).",
        validation_alias=AliasChoices("LIVEKIT_URL", "livekit_url"),
    )
    server_url: Optional[str] = Field(
        default=None,
        description="The HTTP URL for server-side API calls (defaults to converting ws:// to http://).",
        validation_alias=AliasChoices("LIVEKIT_SERVER_URL", "livekit_server_url"),
    )
    api_key: str = Field(
        default="",
        description="The API key for authenticating with the LiveKit server.",
        validation_alias=AliasChoices("LIVEKIT_API_KEY", "livekit_api_key"),
    )
    api_secret: str = Field(
        default="",
        description="The API secret for authenticating with the LiveKit server.",
        validation_alias=AliasChoices("LIVEKIT_API_SECRET", "livekit_api_secret"),
    )

    backend_url: str = Field(
        default="http://localhost:8000",
        description="The URL of the backend service that LiveKit agents will connect to.",
        validation_alias=AliasChoices("LIVEKIT_BACKEND_URL", "livekit_backend_url"),
    )

    # AI Provider API Keys (for LiveKit agents)
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="The API key for Gemini services (used by LiveKit voice agent).",
        validation_alias=AliasChoices("LIVEKIT_GEMINI_API_KEY", "GOOGLE_API_KEY", "gemini_api_key"),
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="The API key for OpenAI services (used by LiveKit voice agent).",
        validation_alias=AliasChoices("LIVEKIT_OPENAI_API_KEY", "OPENAI_API_KEY", "openai_api_key"),
    )
    deepgram_api_key: Optional[str] = Field(
        default=None,
        description="The API key for Deepgram STT services.",
        validation_alias=AliasChoices("LIVEKIT_DEEPGRAM_API_KEY", "DEEPGRAM_API_KEY", "deepgram_api_key"),
    )
    azure_api_key: Optional[str] = Field(
        default=None,
        description="The API key for Azure Speech services.",
        validation_alias=AliasChoices("LIVEKIT_AZURE_API_KEY", "AZURE_SPEECH_KEY", "azure_api_key"),
    )
    azure_region: Optional[str] = Field(
        default=None,
        description="The Azure region for Speech services.",
        validation_alias=AliasChoices("LIVEKIT_AZURE_REGION", "AZURE_SPEECH_REGION", "azure_region"),
    )

    # Model Configuration
    deepgram_model: str = Field(
        default="nova-2",
        description="The Deepgram model to use for speech-to-text.",
        validation_alias=AliasChoices("LIVEKIT_DEEPGRAM_MODEL", "deepgram_model"),
    )
    azure_tts_voice: str = Field(
        default="en-NG-AbeoNeural",
        description="The Azure TTS voice to use for text-to-speech.",
        validation_alias=AliasChoices("LIVEKIT_AZURE_TTS_VOICE", "azure_tts_voice"),
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="The OpenAI model to use for the voice agent.",
        validation_alias=AliasChoices("LIVEKIT_OPENAI_MODEL", "livekit_openai_model"),
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp",
        description="The Gemini model to use for the voice agent.",
        validation_alias=AliasChoices("LIVEKIT_GEMINI_MODEL", "livekit_gemini_model"),
    )

    # Room Settings
    room_empty_timeout: int = Field(
        default=600,
        description="Timeout in seconds before an empty room is closed.",
        validation_alias=AliasChoices("LIVEKIT_ROOM_EMPTY_TIMEOUT", "livekit_room_empty_timeout"),
    )
    room_max_participants: int = Field(
        default=20,
        description="Maximum number of participants per room.",
        validation_alias=AliasChoices("LIVEKIT_ROOM_MAX_PARTICIPANTS", "livekit_room_max_participants"),
    )

    # ============================================================
    # Computed Properties
    # ============================================================

    @computed_field
    @property
    def http_url(self) -> str:
        """Get HTTP URL for server-side API calls."""
        if self.server_url:
            return self.server_url
        # Convert ws:// to http:// or wss:// to https://
        return self.url.replace("ws://", "http://").replace("wss://", "https://")

    @computed_field
    @property
    def has_credentials(self) -> bool:
        """Check if basic LiveKit credentials are configured."""
        return bool(self.api_key and self.api_secret)

    @computed_field
    @property
    def has_deepgram(self) -> bool:
        """Check if Deepgram STT is configured."""
        return bool(self.deepgram_api_key)

    @computed_field
    @property
    def has_backend(self) -> bool:
        """Check if backend URL is configured."""
        return bool(self.backend_url)

    @computed_field
    @property
    def has_openai(self) -> bool:
        """Check if OpenAI is configured for voice agent."""
        return bool(self.openai_api_key)

    @computed_field
    @property
    def has_gemini(self) -> bool:
        """Check if Gemini is configured for voice agent."""
        return bool(self.gemini_api_key)

    @computed_field
    @property
    def has_azure_tts(self) -> bool:
        """Check if Azure TTS is configured."""
        return bool(self.azure_api_key and self.azure_region)

    @computed_field
    @property
    def has_llm(self) -> bool:
        """Check if at least one LLM provider is configured."""
        return self.has_openai or self.has_gemini

    @computed_field
    @property
    def is_fully_configured(self) -> bool:
        """Check if LiveKit is fully configured for voice agent operation."""
        return all([
            self.has_credentials,
            self.has_deepgram,  # Need STT
            self.has_llm,  # Need LLM
            self.has_azure_tts,  # Need TTS
            self.has_backend,  # Need backend URL
        ])

    def get_preferred_llm_provider(self) -> str | None:
        """Get the preferred LLM provider based on available credentials."""
        if self.has_gemini:
            return "gemini"
        if self.has_openai:
            return "openai"
        return None
