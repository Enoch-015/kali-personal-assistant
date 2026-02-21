# Kali Personal Assistant – AI service

FastAPI + LangGraph worker that orchestrates AI workflows for the Kali Personal Assistant. The service can run requests synchronously (HTTP) or asynchronously (Redis event bus) and ships with governance, memory, and plugin dispatch built in.

## What actually happens today

Each run flows through a LangGraph state machine (`src/orchestration/graph.py`):

1) **Intake**: Natural language prompts are interpreted into `OrchestrationRequest` objects; structured requests skip interpretation.
2) **Routing**: A reasoning helper chooses a workflow (`broadcast` when audience is present; otherwise `generic-task`, or a caller-provided workflow).
3) **Policy check**: Policy directives from Mongo (or in-memory fallback) are applied. Blocks or human-approval flags halt early.
4) **Context fetch**: Pulls memory via Graphiti if enabled; otherwise emits demo snippets. Validation marks relevance.
5) **Planning + reflection**: Produces a short action plan and a reflection summary for observability.
6) **Plugin selection + rendering**: Picks a plugin (caller override, channel-based, or demo), renders a message template, and lets the reasoning helper refine the dispatch plan.
7) **Dispatch**: Executes the chosen plugin. Bundled options: `demo-messaging` (simulated delivery; aliases `demo`, `whatsapp`) and `resend-email` (real email when RESEND_* is configured; dry-run otherwise).
8) **Review loop**: A sentinel reviews results, policy flags, and context quality. The review agent may retry the workflow (with routed context) up to `review_max_retries` (default 1) or finish.
9) **Memory update**: Writes a summary back to Graphiti when enabled; otherwise no-op.
10) **Finalize**: Marks status and emits completion events.

Async runs are published to Redis (`kali:agent.requests`); the orchestrator consumes, executes the graph, and publishes status/state to `kali:agent.status`. Sync runs execute inline and return serialized state.

## Endpoints (FastAPI `src/main.py`)

- `GET /` health banner.
- `GET /health` liveness probe.
- `POST /orchestration/requests?mode=async|sync` – structured `OrchestrationRequest` entrypoint. Async enqueues to Redis; sync runs the graph and returns state.
- `POST /router/requests?mode=async|sync` – same as above but tags metadata.source=`router`.
- `POST /ai/graph/invoke?mode=sync|async` – accepts `NaturalLanguageGraphRequest` (prompt + hints) or structured payload; adds metadata.source=`ai_graph_invoke` and routes through the same LangGraph.
- `GET /orchestration/runs/{run_id}` – fetch latest serialized state (from LangGraph checkpoint).

## Runtime components

- **LangGraph**: in-memory checkpointing by default; configurable via `LANGGRAPH_*` settings. Thread IDs map to run IDs.
- **Redis event bus**: Pub/Sub channels are namespaced from `RedisSettings` (see `src/config/settings.py`). Required for async mode.
- **Reasoning helper**: Pure-Python heuristics with optional LLM calls when an async-capable model is configured (see `configure_reasoning_from_settings`).
- **Policy engine**: Pulls user-captured directives from Mongo when available; otherwise uses an in-memory store. Detects “never do …” blocks and “tell me if …” notifications.
- **Memory service**: Wraps Graphiti when `GRAPHITI_ENABLED=true`; otherwise returns demo snippets. Also persists summaries back to Graphiti after successful runs.
- **Plugins**: Registry pattern (`src/orchestration/plugins/base.py`). Built-ins:
  - `demo-messaging`: Simulated dispatch; used as default/alias for `demo` and `whatsapp` channels.
  - `resend-email`: Real email via Resend. Dry-run unless `RESEND_DELIVER=true` and `RESEND_API_KEY` set.

## Running locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# start Redis (local) then launch the API
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
# or use the repo script
pnpm dev:api
```

Visit `http://localhost:8000/docs` for Swagger and `http://localhost:8000/redoc` for ReDoc.

## Key configuration (env)

- Redis: `REDIS_URL`, `REDIS_CHANNEL_PREFIX` (defaults: `redis://localhost:6379/0`, `kali`).
- LangGraph: `LANGGRAPH_CHECKPOINT_STORE` (`memory`|`sqlite`), `LANGGRAPH_CHECKPOINT_PATH`, `LANGGRAPH_MAX_CONCURRENCY`.
- Graphiti (optional): `GRAPHITI_ENABLED`, `GRAPHITI_LLM_PROVIDER` (`openai|gemini|azure|anthropic|groq|ollama|generic`), Neo4j creds, `GRAPHITI_GROUP_ID`, `GRAPHITI_BUILD_INDICES`, search limits, plus provider-specific keys (OpenAI, Azure, Gemini, Anthropic, Groq, Ollama, generic OpenAI-compatible).
- Mongo policy store (optional): `MONGO_URI`, `MONGO_DATABASE`, `MONGO_POLICIES_COLLECTION`, `MONGO_ENABLED`.
- Resend email: `RESEND_API_KEY`, `RESEND_FROM_ADDRESS`, `RESEND_DEFAULT_RECIPIENT`, `RESEND_DELIVER` (false = dry run).
- Review retries: `REVIEW_MAX_RETRIES` (defaults to 1).

All env vars are loaded from `apps/ai/.env` if present.

## Project layout (trimmed)

```
apps/ai/
├── src/
│   ├── main.py                 # FastAPI entrypoint + endpoints
│   ├── config/settings.py      # Typed settings (Redis, LangGraph, Graphiti, Mongo, Resend)
│   ├── event_bus/redis_bus.py  # Redis Pub/Sub wrapper
│   ├── orchestration/
│   │   ├── graph.py            # LangGraph definition + workflow edges
│   │   ├── memory.py           # Graphiti-backed memory provider with demo fallback
│   │   ├── policy.py           # Policy store/engine + feedback capture
│   │   ├── reasoning.py        # Reasoning helper + optional LLM hooks
│   │   ├── review.py           # Sentinel + review agent (retries/human checks)
│   │   └── plugins/            # Plugin registry, demo + Resend email
│   └── services/
│       ├── orchestrator.py     # Agent orchestrator, async consumer, state serialization
│       ├── graphiti_client.py  # Optional Graphiti SDK wrapper
│       └── redis_client.py     # Redis connection helper for tests
├── requirements.txt
└── README.md (this file)
```
