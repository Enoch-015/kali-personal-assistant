"""Provider registries for dynamic, extensible settings.

Sub-packages:
    llm/            – LLM providers  (OpenAI, Gemini, Anthropic, …)
    graph_stores/   – Graph database providers  (Neo4j, …)
    tts/            – Text-to-speech providers  (Azure, …)
    stt/            – Speech-to-text providers  (Deepgram, …)

Adding a new provider = one new file in the correct sub-package.
The ``__init_subclass__`` hook auto-registers it in the parent's registry.
"""

# ── LLM providers ─────────────────────────────────────────────
from .llm import (
    BaseLLMProvider,
    load_llm_provider,
    get_available_providers,
    OpenAIProvider,
    GeminiProvider,
    AnthropicProvider,
    GroqProvider,
    OllamaProvider,
    AzureOpenAIProvider,
    GenericProvider,
)

# ── Graph store providers ────────────────────────────────────
from .graph_stores import (
    BaseGraphStore,
    load_graph_store,
    get_available_graph_stores,
    Neo4jStore,
)

# ── TTS providers ────────────────────────────────────────────
from .tts import (
    BaseTTSProvider,
    load_tts_provider,
    get_available_tts_providers,
    AzureTTSProvider,
    CartesiaTTSProvider,
)

# ── STT providers ────────────────────────────────────────────
from .stt import (
    BaseSTTProvider,
    load_stt_provider,
    get_available_stt_providers,
    DeepgramSTTProvider,
)

__all__ = [
    # LLM
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
    # Graph stores
    "BaseGraphStore",
    "load_graph_store",
    "get_available_graph_stores",
    "Neo4jStore",
    # TTS
    "BaseTTSProvider",
    "load_tts_provider",
    "get_available_tts_providers",
    "AzureTTSProvider",
    "CartesiaTTSProvider",
    # STT
    "BaseSTTProvider",
    "load_stt_provider",
    "get_available_stt_providers",
    "DeepgramSTTProvider",
]
