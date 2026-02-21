"""LLM provider registry with auto-discovery via __init_subclass__."""

from .base import BaseLLMProvider
from .loader import load_llm_provider, get_available_providers

# Import all providers to trigger registration
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .anthropic import AnthropicProvider
from .groq import GroqProvider
from .ollama import OllamaProvider
from .azure import AzureOpenAIProvider
from .generic import GenericProvider

__all__ = [
    "BaseLLMProvider",
    "load_llm_provider",
    "get_available_providers",
    "OpenAIProvider",
    "GeminiProvider",
    "AnthropicProvider",
    "GroqProvider",
    "OllamaProvider",
    "AzureOpenAIProvider",
    "GenericProvider",
]
