# AI Background Worker Endpoint Documentation (current behavior)

The `/ai/graph/invoke` endpoint drives the LangGraph-based orchestrator that powers the AI worker. It accepts natural language prompts (or structured payloads) and runs them through the same pipeline used by `/orchestration/requests`, with optional async execution over Redis.

## Endpoint Details

### POST `/ai/graph/invoke`

Invokes the AI graph. Accepts either a natural language `prompt` (wrapped in `NaturalLanguageGraphRequest`) or a structured orchestration payload.

**Query Parameters:**
- `mode` (optional): `sync` (default) runs the graph inline and returns full state; `async` enqueues on Redis and returns a `run_id`.

**Request Body (natural language path):**

```typescript
{
  request_id?: string;           // auto-generated UUID if omitted
  prompt: string;                // required natural language instruction
  hints?: {
    channel?: string;            // preferred channel/plugin hint
    audience?: {
      recipients?: string[];
      segment_id?: string;
    };
    payload?: {
      template?: string;
      variables?: Record<string, any>;
      [key: string]: any;
    };
    metadata?: Record<string, any>;
  };
}
```

**Structured path:** You can also send the full `OrchestrationRequest` shape used by `/orchestration/requests`; the endpoint adds `metadata.source = "ai_graph_invoke"` automatically.

## Pipeline (LangGraph) as coded

1. `interpret_request`: NL → `OrchestrationRequest` (or passthrough for structured).
2. `route_request`: Choose workflow (`broadcast` when audience exists; metadata override respected; else `generic-task`).
3. `policy_check`: Apply directives from Mongo-backed store (in-memory fallback); may block or require human.
4. `fetch_context`: Retrieve memory from Graphiti when enabled; otherwise demo snippets; validate relevance.
5. `plan_actions`: Build a minimal action plan.
6. `agent_reflection`: Summarize reasoning/risks for observability.
7. `select_plugin`: Pick plugin (metadata override > channel default > `demo-messaging`).
8. `render_payload`: Render message/template (template + variables fallback when no LLM).
9. `execute_plugin` (if plugin chosen): Dispatch via plugin registry (bundled: `demo-messaging`, `resend-email`).
10. `review_outcome`: Sentinel governance pass (categorizes issues, recommendations, routing context).
11. `review_agent`: Decide RETRY vs COMPLETE; retries loop back to routing with state cleanup and `retry_count` incremented.
12. `update_memory`: Persist summary to Graphiti when enabled; no-op otherwise.
13. `finalize`: Mark completion and emit status.

Async mode: payload is published to `kali:agent.requests`; results are published to `kali:agent.status`. Sync mode runs inline and returns serialized state.

## Example Usage

### Example 1: Async Mode - Queue a Background Task

**Request:**
```bash
curl -X POST "http://localhost:8000/ai/graph/invoke?mode=async" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Send a status update email to user@example.com and admin@example.com with the current account status.",
    "hints": {
      "channel": "email",
      "audience": {
        "recipients": ["user@example.com", "admin@example.com"]
      },
      "payload": {
        "template": "Hello {name}, your status is: {status}",
        "variables": {
          "name": "John Doe",
          "status": "Active"
        }
      },
      "metadata": {
        "user_id": "12345",
        "priority": "normal"
      }
    }
  }'
```

**Response:**
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "metadata": {
    "user_id": "12345",
    "priority": "normal",
    "source": "ai_graph_invoke"
  }
}
```

**Query Status:**
```bash
curl "http://localhost:8000/orchestration/runs/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### Example 2: Sync Mode - Wait for Completion

**Request:**
```bash
curl -X POST "http://localhost:8000/ai/graph/invoke?mode=sync" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Broadcast tonight\'s maintenance notice to +15550001111 and +15550002222 on WhatsApp.",
    "hints": {
      "channel": "whatsapp",
      "audience": {
        "recipients": ["+15550001111", "+15550002222"]
      },
        "payload": {
          "template": "Broadcast: {message}",
          "variables": {
            "message": "System maintenance scheduled for tonight"
          }
        }
    }
  }'
```

**Response:**
```json
{
  "run_id": "b2c3d4e5-f6g7-8901-bcde-fg2345678901",
  "status": "completed",
  "state": {
    "request": { /* original request */ },
    "status": "completed",
    "selected_workflow": "broadcast",
    "policy_decision": {
      "allowed": true,
      "reason": "Request satisfies policy checks"
    },
    "planned_actions": [
      {
        "action": "render_message",
        "target": "whatsapp"
      },
      {
        "action": "dispatch_to_recipients",
        "count": 2
      }
    ],
    "analysis_summary": "Broadcasting message to 2 WhatsApp recipients",
    "selected_plugin": "demo-messaging",
    "rendered_message": "Broadcast: System maintenance scheduled for tonight",
    "plugin_result": {
      "plugin_name": "demo-messaging",
      "dispatched_count": 2,
      "failed": [],
      "metadata": {}
    },
    "review_feedback": {
      "approved": true,
      "requires_human": false,
      "summary": "Workflow completed successfully"
    },
    "memory_updates": [
      {
        "summary": "Broadcast sent to 2 recipients via WhatsApp",
        "annotations": {},
        "tokens_used": 150
      }
    ]
  }
}
```

### Example 3: Minimal Request

**Request:**
```bash
curl -X POST "http://localhost:8000/ai/graph/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Process this generic task for me."
  }'
```

**Response:**
```json
{
  "run_id": "c3d4e5f6-g7h8-9012-cdef-gh3456789012",
  "status": "completed",
  "state": { /* full state */ }
}
```

### Email delivery via Resend

- Plugin: `resend-email` (bundled). Uses Resend API when configured; otherwise dry-run.
- Configure in `apps/ai/.env`:
  - `RESEND_API_KEY` (required for live sends)
  - `RESEND_FROM_ADDRESS` (default from)
  - `RESEND_DEFAULT_RECIPIENT` (fallback when no recipients provided)
  - `RESEND_DELIVER=true` to enable live sends; defaults to dry-run for safety.

### Memory via Graphiti (optional)

- Enable with `GRAPHITI_ENABLED=true` plus Neo4j + provider credentials (OpenAI/Gemini/Azure/Anthropic/Groq/Ollama/generic OpenAI-compatible).
- Context fetch uses Graphiti searches; memory updates persist summaries back to Graphiti with optional `GRAPHITI_GROUP_ID`.

## Python Client Example

```python
import httpx
import asyncio
from typing import Dict, Any

async def invoke_ai_graph(
  prompt: str,
  mode: str = "sync",
  hints: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
  """Invoke the AI graph endpoint with a natural language prompt."""
  async with httpx.AsyncClient() as client:
    request_data = {"prompt": prompt}
    if hints:
      request_data["hints"] = hints

    response = await client.post(
      f"http://localhost:8000/ai/graph/invoke?mode={mode}",
      json=request_data,
    )
    response.raise_for_status()
    return response.json()

# Usage
async def main():
  result = await invoke_ai_graph(
    prompt="Email user@example.com with a friendly hello message.",
    mode="sync",
    hints={
      "channel": "email",
      "audience": {"recipients": ["user@example.com"]},
      "payload": {
        "template": "Hello {name}!",
        "variables": {"name": "World"}
      }
    },
  )
  print(f"Status: {result['status']}")
  print(f"Run ID: {result['run_id']}")

asyncio.run(main())
```

## JavaScript/TypeScript Client Example

```typescript
interface AIGraphResponse {
  run_id: string;
  status: string;
  state?: any;
  metadata?: Record<string, any>;
}

interface GraphInvocationRequest {
  prompt: string;
  hints?: {
    channel?: string;
    audience?: {
      recipients?: string[];
      segment_id?: string;
    };
    payload?: Record<string, any>;
    metadata?: Record<string, any>;
  };
}

async function invokeAIGraph(
  request: GraphInvocationRequest,
  mode: 'sync' | 'async' = 'sync'
): Promise<AIGraphResponse> {
  const response = await fetch(
    `http://localhost:8000/ai/graph/invoke?mode=${mode}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    throw new Error(`AI Graph invocation failed: ${response.statusText}`);
  }

  return response.json();
}

// Usage
const result = await invokeAIGraph({
  prompt: 'Send a reminder email to user@example.com about completing their profile.',
  hints: {
    channel: 'email',
    audience: {
      recipients: ['user@example.com']
    },
    payload: {
      template: 'Reminder: {task}',
      variables: { task: 'Complete your profile' }
    }
  }
}, 'async');

console.log('Run ID:', result.run_id);
console.log('Status:', result.status);
```

## Error Handling

### 422 Validation Error
**Cause:** Invalid request body (e.g., missing required `prompt` field)

**Example:**
```json
{
  "detail": [
    {
  "loc": ["body", "prompt"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
**Cause:** Graph execution failed (e.g., missing plugin, provider error)

### 503 Service Unavailable
**Cause:** Orchestrator is not available (e.g., startup not complete)

**Example:**
```json
{
  "detail": "Orchestrator not available"
}
```

## Best practices

1) Prefer `async` for long-running tasks; poll `/orchestration/runs/{run_id}` on the status channel.
2) Provide hints (channel, audience, payload, metadata) to reduce interpretation ambiguity.
3) Include identifiers (user_id/session_id) in metadata; `source: "ai_graph_invoke"` is added automatically.
4) Inspect `review_feedback` and `working_notes` in sync responses to see why a retry happened or why a plugin was chosen.
5) Set `RESEND_DELIVER=false` (default) in non-prod to avoid accidental sends; enable only when ready.

## Integration with Other Endpoints

### Related Endpoints

- **`POST /orchestration/requests`**: General orchestration endpoint (similar functionality)
- **`GET /orchestration/runs/{run_id}`**: Query the state of a workflow run
- **`POST /router/requests`**: Router-specific workflow trigger

### When to Use `/ai/graph/invoke`

Use this endpoint when you:
- Want explicit documentation about invoking the AI worker
- Need direct access to the LangGraph orchestration pipeline
- Want to emphasize that you're triggering AI-powered processing
- Prefer the default sync mode behavior

## Testing

The endpoint includes comprehensive test coverage. To run the tests:

```bash
cd apps/ai
python -m pytest tests/test_ai_graph_endpoint.py -v
```

## Interactive Documentation

Visit the auto-generated API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Explore all available endpoints
- View request/response schemas
- Test endpoints directly in the browser
- Download OpenAPI specification

## Logging

- Request received with prompt and request_id
- Execution mode (sync/async)
- Completion status
- Errors with stack traces

Check logs for debugging:
```bash
# When running with uvicorn
uvicorn src.main:app --reload --log-level debug
```

## Configuration

The AI graph uses settings from environment variables:

### Redis Configuration
```bash
export REDIS_URL=redis://localhost:6379/0
export REDIS_CHANNEL_PREFIX=kali
```

### LLM Provider (for Graphiti/Memory)
```bash
export GRAPHITI_ENABLED=true
export OPENAI_API_KEY=your_api_key
# Or use other providers: gemini, anthropic, azure, etc.
```

See the main README for complete configuration options.
