"""
Kali Personal Assistant - Configuration Package

Provides unified configuration for all Kali apps with per-app .env overrides
and a **provider-registry pattern** for dynamic settings (LLM providers,
graph stores, TTS, STT, etc.).

Quick start::

    from config import get_settings
    settings = get_settings("ai")  # or "voice", "web"

    # Access the LLM provider selected for Graphiti
    if settings.graphiti.llm:
        print(settings.graphiti.llm.provider)   # "openai", "gemini", …
        print(settings.graphiti.llm.is_configured)

    # Access the graph store
    if settings.graphiti.graph_store:
        print(settings.graphiti.graph_store.provider)  # "neo4j"

    # Access LiveKit providers (mutually exclusive LLM)
    if settings.livekit.llm:
        print(settings.livekit.llm.provider)  # "openai" or "gemini"
    if settings.livekit.tts:
        print(settings.livekit.tts.provider)  # "azure"
    if settings.livekit.stt:
        print(settings.livekit.stt.provider)  # "deepgram"

    # Load settings from Vault (production)
    from config import load_settings_from_vault
    settings = await load_settings_from_vault("ai")
"""

# --- Main entry points ---------------------------------------------------
from .settings import (
    Settings,
    get_settings,
    clear_settings_cache,
)

# --- Service settings -----------------------------------------------------
from .services import (
    RedisSettings,
    MongoSettings,
    ResendSettings,
    LangGraphSettings,
    GraphitiSettings,
    LiveKitSettings,
    # Type aliases
    LLMProvider,
    GraphStoreProvider,
    LiveKitLLMProvider,
    TTSProvider,
    STTProvider,
)

# --- Provider registries --------------------------------------------------
from .providers import (
    # LLM
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
    # Graph stores
    BaseGraphStore,
    load_graph_store,
    get_available_graph_stores,
    Neo4jStore,
    # TTS
    BaseTTSProvider,
    load_tts_provider,
    get_available_tts_providers,
    AzureTTSProvider,
    # STT
    BaseSTTProvider,
    load_stt_provider,
    get_available_stt_providers,
    DeepgramSTTProvider,
)

# --- Vault ----------------------------------------------------------------
from .vault_settings import (
    VaultSettings,
    VaultClient,
    get_vault_client,
    get_vault_client_sync,
    clear_vault_client,
    safe_log_secrets,
)

from .vault_loader import (
    load_settings_from_vault,
    load_settings_from_vault_sync,
    load_vault_settings_dict,
    get_vault_client_for_service,
    ServiceType,
)

__all__ = [
    # Main
    "Settings",
    "get_settings",
    "clear_settings_cache",
    # Services
    "RedisSettings",
    "MongoSettings",
    "ResendSettings",
    "LangGraphSettings",
    "GraphitiSettings",
    "LiveKitSettings",
    # Type aliases
    "LLMProvider",
    "GraphStoreProvider",
    "LiveKitLLMProvider",
    "TTSProvider",
    "STTProvider",
    # LLM Providers
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
    # Graph Stores
    "BaseGraphStore",
    "load_graph_store",
    "get_available_graph_stores",
    "Neo4jStore",
    # TTS
    "BaseTTSProvider",
    "load_tts_provider",
    "get_available_tts_providers",
    "AzureTTSProvider",
    # STT
    "BaseSTTProvider",
    "load_stt_provider",
    "get_available_stt_providers",
    "DeepgramSTTProvider",
    # Vault
    "VaultSettings",
    "VaultClient",
    "get_vault_client",
    "get_vault_client_sync",
    "clear_vault_client",
    "safe_log_secrets",
    # Vault Loader
    "load_settings_from_vault",
    "load_settings_from_vault_sync",
    "load_vault_settings_dict",
    "get_vault_client_for_service",
    "ServiceType",
]
