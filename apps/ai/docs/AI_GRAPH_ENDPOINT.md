# AI Background Worker Endpoint Documentation

## Overview

The `/ai/graph/invoke` endpoint provides direct access to the Kali Personal Assistant's AI background worker, which is powered by LangGraph. Send natural language instructions such as “Can you help me send…” and the graph will translate them—via an LLM-powered intake stage—into structured orchestration requests that flow through the multi-stage AI pipeline.

## Endpoint Details

### POST `/ai/graph/invoke`

Invokes the AI background worker graph to process a natural language request.

**Query Parameters:**
- `mode` (optional): Execution mode
  - `sync` (default): Blocks until the graph completes and returns the full state
  - `async`: Enqueues the request and returns immediately with a run_id

**Request Body:** Natural language payload

```typescript
{
  request_id?: string; // Auto-generated UUID if not provided
  prompt: string;      // Required natural language instruction ("Can you help me...")
  hints?: {
    channel?: string;  // Optional channel preference (email, whatsapp, etc.)
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

## AI Pipeline Stages

When you invoke the endpoint, your request flows through these stages:

1. **Interpretation (LLM)**: Converts the raw prompt into a structured orchestration request
2. **Routing (LLM-guided)**: Determines the appropriate workflow based on interpreted intent and prior feedback
3. **Policy Check (LLM commentary)**: Runs policy rules and captures governance analysis from the LLM
4. **Context Fetching**: Retrieves relevant context from memory services (Graphiti)
5. **Planning (LLM-guided)**: Generates an action plan for fulfilling the intent
6. **Reflection (LLM)**: Reviews the plan and highlights risks or gaps
7. **Plugin Selection (LLM-guided)**: Chooses the best plugin to execute the plan
8. **Payload Composition (LLM)**: Drafts the outbound message or action payload
9. **Plugin Dispatch**: Executes the planned action with the selected plugin
10. **Review (LLM sentinel)**: Validates the outcome and determines if retry is needed
11. **Memory Update**: Persists learned information to the knowledge graph

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
**Cause:** Graph execution failed

**Example:**
```json
{
  "detail": "AI graph invocation failed: Plugin 'invalid-plugin' not found"
}
```

### 503 Service Unavailable
**Cause:** Orchestrator is not available (e.g., startup not complete)

**Example:**
```json
{
  "detail": "Orchestrator not available"
}
```

## Best Practices

1. **Use Async Mode for Long-Running Tasks**: If the workflow might take significant time, use async mode and poll the status endpoint.

2. **Provide Helpful Hints**: Supply audience, channel, payload, or metadata hints when you have them—the LLM will merge hints with its interpretation.

3. **Include Metadata**: Add identifiers like `user_id` or `session_id` for observability; the endpoint automatically adds `source: "ai_graph_invoke"`.

4. **Handle Retries**: The orchestrator includes intelligent retry logic, but you should still implement client-side retry for network errors.

5. **Monitor Status**: When using async mode, poll the `/orchestration/runs/{run_id}` endpoint to track progress.

6. **Review State**: In sync mode, inspect the returned `review_feedback` and interpretation notes to understand how the LLM framed your request.

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
