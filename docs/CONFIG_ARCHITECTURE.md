# Config Package Architecture

> `apps/config/` — Centralized, registry-driven configuration for every Kali service.

This document explains the structure of the config package, the design decisions behind it, and how to extend it when adding new providers or services.

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Design Principles](#design-principles)
4. [Provider Registry Pattern](#provider-registry-pattern)
5. [Discriminated Unions](#discriminated-unions)
6. [Service Settings](#service-settings)
7. [Settings Composition](#settings-composition)
8. [Vault Integration](#vault-integration)
9. [How to Add a New Provider](#how-to-add-a-new-provider)
10. [How to Add a New Service](#how-to-add-a-new-service)

---

## Overview

The config package is the **single source of truth** for all runtime configuration across every Kali app (`ai`, `voice`, `web`). It solves three problems:

1. **No if/else chains** — Adding a new LLM, TTS, or graph database doesn't require touching existing code.
2. **Only validate what's selected** — If you choose Gemini, OpenAI fields aren't validated. Pydantic discriminated unions handle this automatically.
3. **Vault is the source of truth** — All settings (secrets _and_ tuning knobs) live in HashiCorp Vault so the Nuxt admin page can update them at runtime.

---

## Directory Structure

```
apps/config/
├── __init__.py            # Public API — re-exports everything consumers need
├── settings.py            # Root Settings class, env-file loading, caching
├── utils.py               # Coercion helpers (coerce_bool, coerce_str, etc.)
├── vault_settings.py      # VaultClient, VaultSettings, AppRole auth
├── vault_loader.py        # Vault → Settings composition (production path)
│
├── providers/             # Dynamic, registry-based provider models
│   ├── __init__.py        # Re-exports from all sub-packages
│   ├── llm/               # LLM providers (OpenAI, Gemini, Anthropic, …)
│   │   ├── base.py        # BaseLLMProvider — registry + abstract interface
│   │   ├── openai.py      # OpenAIProvider(BaseLLMProvider)
│   │   ├── gemini.py      # GeminiProvider(BaseLLMProvider)
│   │   ├── anthropic.py   # AnthropicProvider(BaseLLMProvider)
│   │   ├── groq.py        # GroqProvider(BaseLLMProvider)
│   │   ├── ollama.py      # OllamaProvider(BaseLLMProvider)
│   │   ├── azure.py       # AzureOpenAIProvider(BaseLLMProvider)
│   │   ├── generic.py     # GenericProvider(BaseLLMProvider)
│   │   └── loader.py      # load_llm_provider() factory function
│   ├── graph_stores/      # Graph database providers (Neo4j, …)
│   │   ├── base.py        # BaseGraphStore — registry + abstract interface
│   │   ├── neo4j.py       # Neo4jStore(BaseGraphStore)
│   │   └── loader.py      # load_graph_store() factory function
│   ├── tts/               # Text-to-Speech providers (Azure, Cartesian later)
│   │   ├── base.py        # BaseTTSProvider — registry + abstract interface
│   │   ├── azure.py       # AzureTTSProvider(BaseTTSProvider)
│   │   └── loader.py      # load_tts_provider() factory function
│   └── stt/               # Speech-to-Text providers (Deepgram, …)
│       ├── base.py        # BaseSTTProvider — registry + abstract interface
│       ├── deepgram.py    # DeepgramSTTProvider(BaseSTTProvider)
│       └── loader.py      # load_stt_provider() factory function
│
└── services/              # Service-level settings models
    ├── __init__.py         # Re-exports all service settings + type aliases
    ├── graphiti.py         # GraphitiSettings (uses LLM + GraphStore unions)
    ├── livekit.py          # LiveKitSettings (uses LLM + TTS + STT unions)
    ├── redis.py            # RedisSettings
    ├── mongo.py            # MongoSettings
    ├── resend.py           # ResendSettings
    └── langgraph.py        # LangGraphSettings
```

### Why two layers — `providers/` vs `services/`?

| Layer | Purpose | Shape changes? | Example |
|-------|---------|---------------|---------|
| **`providers/`** | Individual provider models (one per vendor) | Yes — each vendor has different fields | `OpenAIProvider` has `model`, `small_model`; `GeminiProvider` has `reranker_model` |
| **`services/`** | Aggregate settings for a subsystem | No — the _interface_ is stable, but the _selected provider_ varies | `GraphitiSettings.llm` is always `Optional[LLMProvider]`, but at runtime it might be an `OpenAIProvider` or `GeminiProvider` |

---

## Design Principles

### Open/Closed Principle

The config system is **open for extension, closed for modification**:

- To add a new LLM provider (e.g., Mistral), you create **one new file** (`providers/llm/mistral.py`). No existing file needs editing — the registry auto-discovers it.
- To add a new graph database (e.g., Memgraph), create `providers/graph_stores/memgraph.py`. Graphiti will be able to use it without any changes to `GraphitiSettings`.

### Only Validate What's Selected

Traditional flat settings models validate _all_ fields even when most are irrelevant:

```python
# ❌ Old approach — every field validated, most unused
class LiveKitSettings(BaseModel):
    gemini_api_key: str = ""
    openai_api_key: str = ""        # validated even when using Gemini
    deepgram_api_key: str = ""
    azure_api_key: str = ""         # validated even when using Deepgram for STT
    azure_region: str = ""
    # ... 14 flat fields
```

With discriminated unions, only the active provider's fields exist:

```python
# ✅ New approach — only selected provider is validated
class LiveKitSettings(BaseModel):
    llm: Optional[LiveKitLLMProvider] = None   # OpenAI OR Gemini, never both
    tts: Optional[TTSProvider] = None           # Azure (Cartesian later)
    stt: Optional[STTProvider] = None           # Deepgram (others later)
```

### Vault as Single Source of Truth

Every service setting (not just secrets) is stored in Vault. This means the Nuxt admin page can update model names, search limits, concurrency settings, etc. without redeploying. Each service settings class has a `from_vault(secrets)` factory method.

---

## Provider Registry Pattern

Each provider category (LLM, graph store, TTS, STT) uses the same pattern:

### 1. Base class with auto-registration

```python
# providers/llm/base.py
class BaseLLMProvider(BaseModel):
    _registry: ClassVar[dict[str, type["BaseLLMProvider"]]] = {}
    provider: str  # discriminator field

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "provider_name", None)
        if name:
            BaseLLMProvider._registry[name] = cls
```

When Python imports a subclass, `__init_subclass__` fires and registers it automatically. No manual mapping needed.

### 2. Concrete provider

```python
# providers/llm/openai.py
class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"                     # triggers auto-registration
    provider: Literal["openai"] = "openai"       # Pydantic discriminator value

    api_key: str = ""
    model: str = "gpt-4o"

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "OpenAIProvider":
        return cls(
            api_key=secrets.get("openai-api-key", ""),
            model=secrets.get("openai-model", "gpt-4o"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
```

### 3. Factory function

```python
# providers/llm/loader.py
def load_llm_provider(provider: str, *, secrets=None, env=None):
    cls = BaseLLMProvider._registry.get(provider.lower())
    if cls is None:
        raise ValueError(f"Unknown LLM provider: {provider}")
    if secrets:
        return cls.from_vault(secrets)
    if env:
        return cls.from_env(env)
```

### How the registry is populated

The `providers/__init__.py` file imports each concrete module, which triggers `__init_subclass__`:

```python
# providers/__init__.py
from .llm import *          # imports openai.py, gemini.py, etc. → registers them
from .graph_stores import *  # imports neo4j.py → registers it
from .tts import *           # imports azure.py → registers it
from .stt import *           # imports deepgram.py → registers it
```

And `settings.py` imports the providers package on startup:

```python
import config.providers as _providers  # noqa: F401 — triggers registration
```

---

## Discriminated Unions

Pydantic's discriminated unions let you say "this field is _one of_ these types, and the `provider` field tells you which one":

```python
# In services/graphiti.py
LLMProvider = Annotated[
    Union[OpenAIProvider, GeminiProvider, AnthropicProvider, ...],
    Field(discriminator="provider"),
]

GraphStoreProvider = Annotated[
    Union[Neo4jStore],
    Field(discriminator="provider"),
]

class GraphitiSettings(BaseModel):
    llm: Optional[LLMProvider] = None
    graph_store: Optional[GraphStoreProvider] = None
```

When you pass `{"provider": "openai", "api_key": "sk-..."}`, Pydantic knows to validate it as `OpenAIProvider`. If you pass `{"provider": "gemini", ...}`, it validates as `GeminiProvider`. Fields that don't belong to the selected provider are never checked.

### Mutual Exclusivity (LiveKit LLM)

LiveKit's `llm` field is a union of _only_ `OpenAIProvider | GeminiProvider`. Setting `preferred-llm: gemini` in Vault means only Gemini is loaded — OpenAI keys are ignored entirely:

```python
# In services/livekit.py
LiveKitLLMProvider = Annotated[
    Union[OpenAIProvider, GeminiProvider],   # only these two
    Field(discriminator="provider"),
]
```

---

## Service Settings

Each service model in `services/` is a self-contained Pydantic `BaseModel` with:

| Method | Purpose |
|--------|---------|
| `from_vault(secrets)` | Build from Vault dict — **production path** |
| `from_env(env)` | Build from env dict — **dev fallback** |
| `has_credentials` / `is_configured` | Introspection for auto-enable/disable |

### GraphitiSettings

Owns the knowledge graph configuration:
- `llm: Optional[LLMProvider]` — which LLM to use for entity extraction
- `graph_store: Optional[GraphStoreProvider]` — which graph database (Neo4j today)
- `enabled`, `group_id`, `build_indices_on_startup`, `search_limit`
- Backward-compat properties: `neo4j_uri`, `neo4j_user`, `neo4j_password` delegate to `graph_store`

### LiveKitSettings

Owns real-time voice AI configuration:
- `llm: Optional[LiveKitLLMProvider]` — OpenAI _or_ Gemini (mutually exclusive)
- `tts: Optional[TTSProvider]` — Azure TTS (Cartesian later)
- `stt: Optional[STTProvider]` — Deepgram STT (others later)
- `api_key`, `api_secret`, `url`, `backend_url`
- Computed: `has_llm`, `has_tts`, `has_stt`, `is_fully_configured`

### Redis / Mongo / Resend / LangGraph

Simpler models with flat fields and a `from_vault()` factory.

---

## Settings Composition

There are two paths to building a complete `Settings` object:

### Production: Vault path (`vault_loader.py`)

```
Vault (databases, python-ai, livekit, shared)
   ↓  raw secret dicts
Each service's from_vault() factory
   ↓  hydrated service models
Settings(redis=..., mongo=..., graphiti=..., livekit=..., ...)
```

```python
# vault_loader.py — simplified
async def load_settings_from_vault(service_type):
    vault = await load_vault_settings_dict(service_type)
    return Settings(
        redis=RedisSettings.from_vault(vault["databases"]),
        mongo=MongoSettings.from_vault(vault["databases"]),
        graphiti=GraphitiSettings.from_vault(
            ai_secrets=vault["python-ai"],
            db_secrets=vault["databases"],
        ),
        livekit=LiveKitSettings.from_vault(livekit_secrets=vault["livekit"]),
        resend=ResendSettings.from_vault(vault["shared"]),
        langgraph=LangGraphSettings.from_vault(vault["python-ai"]),
    )
```

### Development: Env path (`settings.py`)

```
.env files + os.environ
   ↓  merged dict
Settings() → model_validator → _apply_graphiti_overrides / _apply_livekit_overrides
   ↓  calls from_env() factories internally
Settings with hydrated sub-models
```

The `get_settings("ai")` function handles the dev path with `.env` file loading and caching.

---

## Vault Integration

### Vault Paths

| Path | Contains | Used By |
|------|----------|---------|
| `databases` | `redis-url`, `neo4j-uri`, `neo4j-username`, `neo4j-password`, `mongodb-uri` | Redis, Mongo, Graphiti (graph store) |
| `python-ai` | `openai-api-key`, `google-api-key`, `anthropic-api-key`, `graphiti-llm-provider`, model names, Graphiti options | Graphiti (LLM) |
| `livekit` | `api-key`, `api-secret`, `preferred-llm`, `preferred-tts`, `preferred-stt`, provider API keys | LiveKit |
| `shared` | `resend-api-key` | Resend |

### Provider Selection via Vault Keys

The `preferred-*` keys in Vault determine which provider is loaded:

```
# Vault: livekit path
preferred-llm: "gemini"          → loads GeminiProvider
preferred-tts: "azure"           → loads AzureTTSProvider
preferred-stt: "deepgram"        → loads DeepgramSTTProvider

# Vault: python-ai path
graphiti-llm-provider: "openai"  → loads OpenAIProvider for Graphiti
graphiti-graph-store: "neo4j"    → loads Neo4jStore
```

---

## How to Add a New Provider

Example: Adding a **Cartesian TTS** provider.

### Step 1: Create the provider file

```python
# apps/config/providers/tts/cartesian.py
from __future__ import annotations
from typing import Any, ClassVar, Literal
from pydantic import Field
from .base import BaseTTSProvider

class CartesianTTSProvider(BaseTTSProvider):
    provider_name: ClassVar[str] = "cartesian"
    provider: Literal["cartesian"] = "cartesian"

    api_key: str = Field(default="", description="Cartesian API key.")
    voice_id: str = Field(default="default", description="Cartesian voice identifier.")

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "CartesianTTSProvider":
        return cls(
            api_key=secrets.get("cartesian-api-key", ""),
            voice_id=secrets.get("cartesian-voice-id", "default"),
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "CartesianTTSProvider":
        return cls(
            api_key=env.get("cartesian_api_key") or env.get("CARTESIAN_API_KEY", ""),
            voice_id=env.get("cartesian_voice_id", "default"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
```

### Step 2: Import it in the package `__init__`

```python
# apps/config/providers/tts/__init__.py
from .cartesian import CartesianTTSProvider  # add this line
```

### Step 3: Add it to the discriminated union

```python
# apps/config/services/livekit.py
from ..providers.tts.cartesian import CartesianTTSProvider

TTSProvider = Annotated[
    Union[AzureTTSProvider, CartesianTTSProvider],  # add to union
    Field(discriminator="provider"),
]
```

### Step 4: Set it in Vault

```
preferred-tts: "cartesian"
cartesian-api-key: "ck-..."
```

**That's it.** No if/else chains, no changes to `settings.py` or `vault_loader.py`.

---

## How to Add a New Service

Example: Adding a **vector store** service.

1. Create `apps/config/services/vector_store.py` with a `VectorStoreSettings(BaseModel)` class and a `from_vault()` classmethod.
2. Add a field to `Settings` in `settings.py`:
   ```python
   vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
   ```
3. Add it to `vault_loader.py`'s `load_settings_from_vault()`:
   ```python
   vector_store=VectorStoreSettings.from_vault(db_secrets)
   ```
4. Re-export from `services/__init__.py` and `config/__init__.py`.

If the service has provider-based options (e.g., Pinecone vs Qdrant), create a `providers/vector_stores/` sub-package following the same base → concrete → loader pattern used by the other registries.

---

## Quick Reference

### Key imports

```python
from config import get_settings, Settings
from config import OpenAIProvider, GeminiProvider, Neo4jStore
from config import AzureTTSProvider, DeepgramSTTProvider
from config import load_settings_from_vault
```

### Check what's registered at runtime

```python
from config import BaseLLMProvider, BaseGraphStore, BaseTTSProvider, BaseSTTProvider

print(BaseLLMProvider._registry)    # {'openai': ..., 'gemini': ..., ...}
print(BaseGraphStore._registry)     # {'neo4j': ...}
print(BaseTTSProvider._registry)    # {'azure': ...}
print(BaseSTTProvider._registry)    # {'deepgram': ...}
```

### Access provider fields

```python
settings = get_settings("ai")

# Graphiti
if settings.graphiti.llm:
    print(settings.graphiti.llm.provider)       # "openai"
    print(settings.graphiti.llm.api_key)        # "sk-..."
if settings.graphiti.graph_store:
    print(settings.graphiti.graph_store.uri)     # "bolt://..."

# LiveKit
if settings.livekit.llm:
    print(settings.livekit.llm.provider)        # "gemini" or "openai"
if settings.livekit.tts:
    print(settings.livekit.tts.region)          # "eastus"
if settings.livekit.stt:
    print(settings.livekit.stt.model)           # "nova-2"
```
