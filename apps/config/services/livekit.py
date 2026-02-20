"""LiveKit configuration settings using provider registries.

``LiveKitSettings`` delegates real-time AI subsystems to discriminated unions:
* **LLM** — currently OpenAI *or* Gemini (mutually exclusive via ``preferred_llm``).
* **TTS** — currently Azure (Cartesian later).
* **STT** — currently Deepgram (others later).

Only the *selected* provider's fields are validated.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field

# ── LLM providers (reuse from graphiti – only a subset for LiveKit) ─────
from ..providers.llm.base import BaseLLMProvider
from ..providers.llm.gemini import GeminiProvider
from ..providers.llm.openai import OpenAIProvider

# ── TTS / STT providers ─────────────────────────────────────────────────
from ..providers.stt.base import BaseSTTProvider
from ..providers.stt.deepgram import DeepgramSTTProvider
from ..providers.tts.azure import AzureTTSProvider
from ..providers.tts.base import BaseTTSProvider

# Discriminated unions scoped to LiveKit
LiveKitLLMProvider = Annotated[
    Union[OpenAIProvider, GeminiProvider],
    Field(discriminator="provider"),
]

TTSProvider = Annotated[
    Union[AzureTTSProvider],
    Field(discriminator="provider"),
]

STTProvider = Annotated[
    Union[DeepgramSTTProvider],
    Field(discriminator="provider"),
]


class LiveKitSettings(BaseModel):
    """LiveKit configuration settings model.

    All provider-specific fields (API keys, model names, regions) are
    encapsulated inside the ``llm``, ``tts``, and ``stt`` sub-models.
    The ``preferred_*`` Vault keys select which concrete provider to load.
    """

    model_config = ConfigDict(populate_by_name=True)

    # ── Core LiveKit Server Settings ─────────────────────────────────────
    enabled: bool = Field(
        default=True,
        description="Whether LiveKit integration is enabled.",
    )
    url: str = Field(
        default="ws://localhost:7880",
        description="WebSocket URL of the LiveKit server (for client connections).",
    )
    server_url: Optional[str] = Field(
        default=None,
        description="HTTP URL for server-side API calls (defaults to ws→http conversion).",
    )
    api_key: str = Field(
        default="",
        description="API key for authenticating with the LiveKit server.",
    )
    api_secret: str = Field(
        default="",
        description="API secret for authenticating with the LiveKit server.",
    )
    backend_url: str = Field(
        default="http://localhost:8000",
        description="URL of the backend service that LiveKit agents connect to.",
    )

    # ── Provider unions (discriminated – mutually exclusive) ─────────────
    llm: Optional[LiveKitLLMProvider] = Field(
        default=None,
        description="LLM provider (OpenAI *or* Gemini). Only the selected provider is validated.",
    )
    tts: Optional[TTSProvider] = Field(
        default=None,
        description="TTS provider (Azure now, Cartesian later).",
    )
    stt: Optional[STTProvider] = Field(
        default=None,
        description="STT provider (Deepgram now, others later).",
    )

    # ── Room Settings ────────────────────────────────────────────────────
    room_empty_timeout: int = Field(
        default=600,
        description="Timeout (seconds) before an empty room is closed.",
    )
    room_max_participants: int = Field(
        default=20,
        description="Maximum participants per room.",
    )

    # ==================================================================
    # Computed properties
    # ==================================================================

    @computed_field
    @property
    def http_url(self) -> str:
        """HTTP URL for server-side API calls."""
        if self.server_url:
            return self.server_url
        return self.url.replace("ws://", "http://").replace("wss://", "https://")

    @computed_field
    @property
    def has_credentials(self) -> bool:
        """Basic LiveKit credentials present."""
        return bool(self.api_key and self.api_secret)

    @computed_field
    @property
    def has_backend(self) -> bool:
        return bool(self.backend_url)

    @computed_field
    @property
    def has_llm(self) -> bool:
        return self.llm is not None and self.llm.is_configured

    @computed_field
    @property
    def has_tts(self) -> bool:
        return self.tts is not None and self.tts.is_configured

    @computed_field
    @property
    def has_stt(self) -> bool:
        return self.stt is not None and self.stt.is_configured

    @computed_field
    @property
    def is_fully_configured(self) -> bool:
        return all([
            self.has_credentials,
            self.has_stt,
            self.has_llm,
            self.has_tts,
            self.has_backend,
        ])

    # Backward-compat helpers
    @computed_field
    @property
    def has_deepgram(self) -> bool:
        return self.stt is not None and self.stt.provider == "deepgram" and self.stt.is_configured

    @computed_field
    @property
    def has_openai(self) -> bool:
        return self.llm is not None and self.llm.provider == "openai" and self.llm.is_configured

    @computed_field
    @property
    def has_gemini(self) -> bool:
        return self.llm is not None and self.llm.provider == "gemini" and self.llm.is_configured

    @computed_field
    @property
    def has_azure_tts(self) -> bool:
        return self.tts is not None and self.tts.provider == "azure" and self.tts.is_configured

    def get_preferred_llm_provider(self) -> str | None:
        """Return the active LLM provider name, or ``None``."""
        return self.llm.provider if self.llm else None

    # ==================================================================
    # Factory helpers
    # ==================================================================

    @classmethod
    def from_vault(cls, *, livekit_secrets: dict[str, Any]) -> "LiveKitSettings":
        """Build ``LiveKitSettings`` entirely from Vault data.

        Parameters
        ----------
        livekit_secrets:
            Vault ``livekit`` path.
            Expected keys: ``api-key``, ``api-secret``, ``url``,
            ``preferred-llm``, ``preferred-tts``, ``preferred-stt``,
            provider-specific API keys and model overrides.
        """
        # LLM — mutually exclusive via preferred-llm
        preferred_llm = (
            livekit_secrets.get("preferred-llm")
            or livekit_secrets.get("preferred_llm")
        )
        llm_instance: BaseLLMProvider | None = None
        if preferred_llm:
            preferred_llm = preferred_llm.lower()
            llm_cls = BaseLLMProvider._registry.get(preferred_llm)
            if llm_cls is not None:
                llm_instance = llm_cls.from_vault(livekit_secrets)

        # TTS
        preferred_tts = (
            livekit_secrets.get("preferred-tts")
            or livekit_secrets.get("preferred_tts")
            or "azure"
        ).lower()
        tts_instance: BaseTTSProvider | None = None
        tts_cls = BaseTTSProvider._registry.get(preferred_tts)
        if tts_cls is not None:
            tts_instance = tts_cls.from_vault(livekit_secrets)
            if not tts_instance.is_configured:
                tts_instance = None

        # STT
        preferred_stt = (
            livekit_secrets.get("preferred-stt")
            or livekit_secrets.get("preferred_stt")
            or "deepgram"
        ).lower()
        stt_instance: BaseSTTProvider | None = None
        stt_cls = BaseSTTProvider._registry.get(preferred_stt)
        if stt_cls is not None:
            stt_instance = stt_cls.from_vault(livekit_secrets)
            if not stt_instance.is_configured:
                stt_instance = None

        return cls(
            enabled=True,
            url=livekit_secrets.get("url", "ws://localhost:7880"),
            server_url=livekit_secrets.get("server-url"),
            api_key=livekit_secrets.get("api-key", ""),
            api_secret=livekit_secrets.get("api-secret", ""),
            backend_url=livekit_secrets.get("backend-url", "http://localhost:8000"),
            llm=llm_instance,
            tts=tts_instance,
            stt=stt_instance,
            room_empty_timeout=int(livekit_secrets.get("room-empty-timeout", 600)),
            room_max_participants=int(livekit_secrets.get("room-max-participants", 20)),
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "LiveKitSettings":
        """Build from an env-dict (model_extra / os.environ merge).

        Used as a dev-mode fallback when Vault is unavailable.
        """
        from ..utils import coerce_bool

        # Determine which LLM to use
        preferred_llm = (
            env.get("livekit_preferred_llm")
            or env.get("LIVEKIT_PREFERRED_LLM")
        )
        llm_instance: BaseLLMProvider | None = None
        if preferred_llm:
            llm_cls = BaseLLMProvider._registry.get(preferred_llm.lower())
            if llm_cls is not None:
                llm_instance = llm_cls.from_env(env)
        else:
            # Auto-detect: prefer gemini if key present, then openai
            gemini_key = env.get("livekit_gemini_api_key") or env.get("GOOGLE_API_KEY")
            openai_key = env.get("livekit_openai_api_key") or env.get("OPENAI_API_KEY")
            if gemini_key:
                llm_instance = GeminiProvider(api_key=gemini_key, model=env.get("livekit_gemini_model", "gemini-2.0-flash-exp"))
            elif openai_key:
                llm_instance = OpenAIProvider(api_key=openai_key, model=env.get("livekit_openai_model", "gpt-4o-mini"))

        # TTS
        tts_instance: BaseTTSProvider | None = None
        azure_key = env.get("livekit_azure_api_key") or env.get("AZURE_SPEECH_KEY")
        azure_region = env.get("livekit_azure_region") or env.get("AZURE_SPEECH_REGION")
        if azure_key and azure_region:
            tts_instance = AzureTTSProvider(
                api_key=azure_key,
                region=azure_region,
                voice=env.get("livekit_azure_tts_voice", "en-NG-AbeoNeural"),
            )

        # STT
        stt_instance: BaseSTTProvider | None = None
        deepgram_key = env.get("livekit_deepgram_api_key") or env.get("DEEPGRAM_API_KEY")
        if deepgram_key:
            stt_instance = DeepgramSTTProvider(
                api_key=deepgram_key,
                model=env.get("livekit_deepgram_model", "nova-2"),
            )

        return cls(
            enabled=coerce_bool(env.get("livekit_enabled", True)),
            url=env.get("livekit_url", "ws://localhost:7880"),
            server_url=env.get("livekit_server_url"),
            api_key=env.get("livekit_api_key", ""),
            api_secret=env.get("livekit_api_secret", ""),
            backend_url=env.get("livekit_backend_url", "http://localhost:8000"),
            llm=llm_instance,
            tts=tts_instance,
            stt=stt_instance,
            room_empty_timeout=int(env.get("livekit_room_empty_timeout", 600)),
            room_max_participants=int(env.get("livekit_room_max_participants", 20)),
        )
