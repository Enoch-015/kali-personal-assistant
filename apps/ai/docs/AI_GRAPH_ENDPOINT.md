# AI Background Worker Endpoint Documentation

## Overview

The `/ai/graph/invoke` endpoint provides direct access to the Kali Personal Assistant's AI background worker, which is powered by LangGraph. This endpoint allows external requests to trigger the orchestration graph that processes user intents through a multi-stage AI pipeline.

## Endpoint Details

### POST `/ai/graph/invoke`

Invokes the AI background worker graph to process an orchestration request.

**Query Parameters:**
- `mode` (optional): Execution mode
  - `sync` (default): Blocks until the graph completes and returns the full state
  - `async`: Enqueues the request and returns immediately with a run_id

**Request Body:** `OrchestrationRequest` object

```typescript
{
  request_id?: string;        // Auto-generated UUID if not provided
  intent: string;             // Required: High-level user intent
  channel?: string;           // Default: "demo" - Target channel (email, whatsapp, etc.)
  audience?: {                // Optional: Target recipients
    recipients: string[];     // List of recipient IDs/addresses
    segment_id?: string;      // Optional: Saved segment identifier
  };
  payload?: {                 // Optional: Request payload
    template?: string;        // Message template with variables
    variables?: object;       // Variables to fill in template
    [key: string]: any;       // Additional custom fields
  };
  metadata?: {                // Optional: Additional metadata
    [key: string]: any;
  };
}
```

## AI Pipeline Stages

When you invoke the endpoint, your request flows through these stages:

1. **Routing**: Determines the appropriate workflow based on the intent
2. **Policy Check**: Validates the request against configured policies
3. **Context Fetching**: Retrieves relevant context from memory services (Graphiti)
4. **Planning**: Generates an action plan for fulfilling the intent
5. **Reflection**: Analyzes and validates the plan
6. **Plugin Selection & Dispatch**: Chooses and executes the appropriate plugin
7. **Review**: Validates the outcome and determines if retry is needed
8. **Memory Update**: Persists learned information to the knowledge graph

## Example Usage

### Example 1: Async Mode - Queue a Background Task

**Request:**
```bash
curl -X POST "http://localhost:8000/ai/graph/invoke?mode=async" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "send_status_update",
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
    "intent": "send_broadcast",
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
    "intent": "process_generic_task"
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
    intent: str,
    mode: str = "sync",
    channel: str = "demo",
    audience: Dict[str, Any] | None = None,
    payload: Dict[str, Any] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Invoke the AI graph endpoint."""
    async with httpx.AsyncClient() as client:
        request_data = {
            "intent": intent,
            "channel": channel,
        }
        if audience:
            request_data["audience"] = audience
        if payload:
            request_data["payload"] = payload
        if metadata:
            request_data["metadata"] = metadata

        response = await client.post(
            f"http://localhost:8000/ai/graph/invoke?mode={mode}",
            json=request_data,
        )
        response.raise_for_status()
        return response.json()

# Usage
async def main():
    result = await invoke_ai_graph(
        intent="send_notification",
        mode="sync",
        channel="email",
        audience={"recipients": ["user@example.com"]},
        payload={
            "template": "Hello {name}!",
            "variables": {"name": "World"}
        }
    )
    print(f"Status: {result['status']}")
    print(f"Run ID: {result['run_id']}")

asyncio.run(main())
```

## JavaScript/TypeScript Client Example

```typescript
interface OrchestrationRequest {
  intent: string;
  channel?: string;
  audience?: {
    recipients: string[];
    segment_id?: string;
  };
  payload?: {
    template?: string;
    variables?: Record<string, any>;
    [key: string]: any;
  };
  metadata?: Record<string, any>;
}

interface AIGraphResponse {
  run_id: string;
  status: string;
  state?: any;
  metadata?: Record<string, any>;
}

async function invokeAIGraph(
  request: OrchestrationRequest,
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
  intent: 'send_reminder',
  channel: 'email',
  audience: {
    recipients: ['user@example.com']
  },
  payload: {
    template: 'Reminder: {task}',
    variables: { task: 'Complete your profile' }
  }
}, 'async');

console.log('Run ID:', result.run_id);
console.log('Status:', result.status);
```

## Error Handling

### 422 Validation Error
**Cause:** Invalid request body (e.g., missing required `intent` field)

**Example:**
```json
{
  "detail": [
    {
      "loc": ["body", "intent"],
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

2. **Include Metadata**: Add relevant metadata like user_id, session_id, etc., for better tracking and debugging.

3. **Handle Retries**: The graph includes intelligent retry logic, but you should still implement client-side retry for network errors.

4. **Monitor Status**: When using async mode, poll the `/orchestration/runs/{run_id}` endpoint to track progress.

5. **Review State**: In sync mode, check the `review_feedback` in the response to ensure the workflow was approved.

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

The endpoint logs key events:
- Request received with intent and request_id
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
