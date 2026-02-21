"""Service configuration models.

Each module in this package defines settings for one infrastructure service.
Service settings use discriminated unions from ``config.providers`` for
provider-based options (LLM, graph stores, TTS, STT).
"""

from .redis import RedisSettings
from .mongo import MongoSettings
from .resend import ResendSettings
from .langgraph import LangGraphSettings
from .livekit import LiveKitSettings
from .graphiti import GraphitiSettings

# Re-export discriminated union type aliases for convenience
from .graphiti import LLMProvider, GraphStoreProvider
from .livekit import LiveKitLLMProvider, TTSProvider, STTProvider

__all__ = [
    "RedisSettings",
    "MongoSettings",
    "ResendSettings",
    "LangGraphSettings",
    "LiveKitSettings",
    "GraphitiSettings",
    # Type aliases
    "LLMProvider",
    "GraphStoreProvider",
    "LiveKitLLMProvider",
    "TTSProvider",
    "STTProvider",
]
