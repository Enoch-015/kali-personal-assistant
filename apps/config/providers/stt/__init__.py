"""STT (speech-to-text) provider registry."""

from .base import BaseSTTProvider
from .loader import load_stt_provider, get_available_stt_providers
from .deepgram import DeepgramSTTProvider

__all__ = [
    "BaseSTTProvider",
    "load_stt_provider",
    "get_available_stt_providers",
    "DeepgramSTTProvider",
]
