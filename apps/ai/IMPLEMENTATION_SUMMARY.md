# AI Orchestration – Implementation Summary (current behavior)

This document reflects what the AI worker does today, based on the code in `apps/ai`.

## End-to-end flow

1) **Intake** (`interpret_request`): Natural language prompts become `OrchestrationRequest` objects; structured requests pass through unchanged.
2) **Routing** (`route_request`): Chooses a workflow (`broadcast` when audience exists, caller-specified when provided, else `generic-task`). Working notes accumulate rationale.
3) **Policy** (`policy_check`): Evaluates directives from Mongo-backed store (in-memory fallback). Can block or require human approval; adds tags and notes.
4) **Memory** (`fetch_context`): Pulls snippets/relations from Graphiti when enabled; otherwise emits demo placeholders. Validates relevance.
5) **Planning + reflection** (`plan_actions`, `agent_reflection`): Builds a small plan and a reflection summary for observability.
6) **Plugin selection + render** (`select_plugin`, `render_payload`): Picks a plugin (metadata override > channel default > `demo-messaging`), renders a message/template.
7) **Dispatch** (`execute_plugin`): Executes the chosen plugin. Bundled plugins: `demo-messaging` (simulated; aliases `demo`, `whatsapp`) and `resend-email` (real email when RESEND_* is set, otherwise dry-run).
8) **Review loop** (`review_outcome`, `review_agent`): Sentinel categorizes issues, recommendations, and routing context. Review agent may RETRY (resets dispatch state, increments `retry_count`) or COMPLETE.
9) **Memory update + finalize** (`update_memory`, `finalize`): Writes summaries back to Graphiti when enabled; marks status and emits completion.

Async requests publish to Redis (`kali:agent.requests`); the orchestrator consumes, runs the graph, and publishes state to `kali:agent.status`. Sync requests run inline and return serialized state.

## Key components

- **Orchestrator** (`src/services/orchestrator.py`): Manages the LangGraph instance, enqueue/run paths, Redis consumer loop, and state serialization.
- **LangGraph** (`src/orchestration/graph.py`): Defines the state machine and stage transitions, including conditional edges for plugin dispatch and review retries.
- **Reasoning helper** (`src/orchestration/reasoning.py`): Heuristic-first; can call an async LLM if configured. Handles interpretation, routing choice, planning, reflection, plugin choice, and payload generation.
- **Policy engine** (`src/orchestration/policy.py`): Pulls directives from Mongo (or memory) and captures feedback directives from incoming requests.
- **Memory service** (`src/orchestration/memory.py`): Graphiti-backed context fetch and memory updates; demo fallback when Graphiti is disabled.
- **Review** (`src/orchestration/review.py`): Sentinel builds `ReviewFeedback` with issues, recommendations, and routing context; review agent decides RETRY/COMPLETE and carries context into reruns.
- **Plugins** (`src/orchestration/plugins/*`): Registry pattern. Built-ins: `demo-messaging`, `resend-email` (Resend API with dry-run by default).
- **Event bus** (`src/event_bus/redis_bus.py`): Thin Redis Pub/Sub wrapper used for async ingestion and status streaming.

## Data that moves between stages

- `request`, `raw_prompt`, `request_hints`
- `working_notes`, `interpretation_notes`, `retry_count`
- `selected_workflow`, `planned_actions`, `analysis_summary`
- `policy_decision`, `requires_human_approval`
- `retrieved_context`, `context_validation`
- `selected_plugin`, `rendered_message`, `plugin_result`
- `review_feedback`, `review_action`, `review_notes`, `routing_context`
- `memory_updates`

## Configuration highlights (env)

- Redis (`REDIS_URL`, prefix/channel overrides)
- LangGraph (`LANGGRAPH_CHECKPOINT_STORE`, `LANGGRAPH_CHECKPOINT_PATH`, `LANGGRAPH_MAX_CONCURRENCY`)
- Graphiti (`GRAPHITI_ENABLED`, provider + Neo4j creds, group ID, build indices, search limits)
- Mongo policy store (`MONGO_URI`, `MONGO_ENABLED`, collection/db names)
- Resend email (`RESEND_API_KEY`, `RESEND_FROM_ADDRESS`, `RESEND_DEFAULT_RECIPIENT`, `RESEND_DELIVER`)
- Review retries (`REVIEW_MAX_RETRIES`)

## Future refinements to consider

- More plugins (SMS/WhatsApp proper, calendar, CRM)
- Persistence-backed LangGraph checkpoints for resilience
- Plugin reliability scoring and routing hints
- Expanded telemetry for plans/retries and policy decisions

## Security/observability notes

- Policy directives and Graphiti credentials are read from env; Graphiti is disabled when credentials are incomplete.
- Resend runs in dry-run unless explicitly enabled, reducing accidental sends during development.
- Redis channels are namespaced; errors during async consumption are logged and surfaced on the status channel.
