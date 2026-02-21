"""TTS (text-to-speech) provider registry."""

from .base import BaseTTSProvider
from .loader import load_tts_provider, get_available_tts_providers
from .azure import AzureTTSProvider
from .cartesia import CartesiaTTSProvider

__all__ = [
    "BaseTTSProvider",
    "load_tts_provider",
    "get_available_tts_providers",
    "AzureTTSProvider",
    "CartesiaTTSProvider",
]
