import logging
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.event_bus.redis_bus import RedisEventBus
from src.orchestration.models import OrchestrationRequest, WorkflowStatus
from src.services.orchestrator import AgentOrchestrator, bootstrap_orchestrator, serialize_state

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kali Personal Assistant API",
    description="FastAPI backend for Kali Personal Assistant",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event() -> None:
    settings = get_settings()
    app.state.settings = settings
    event_bus = RedisEventBus(settings.redis)
    app.state.event_bus = event_bus
    healthy = await event_bus.ping()
    if not healthy:
        logger.warning("Redis event bus is not reachable; orchestrator will still attempt to start")
    app.state.orchestrator = await bootstrap_orchestrator(settings, event_bus)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    orchestrator: AgentOrchestrator | None = getattr(app.state, "orchestrator", None)
    event_bus: RedisEventBus | None = getattr(app.state, "event_bus", None)
    if orchestrator:
        await orchestrator.stop()
    if event_bus:
        await event_bus.close()


async def get_orchestrator() -> AgentOrchestrator:
    orchestrator: AgentOrchestrator | None = getattr(app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orchestrator


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Kali Personal Assistant API"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/orchestration/requests")
async def submit_orchestration_request(
    request: OrchestrationRequest,
    mode: Literal["async", "sync"] = Query("async", description="Execution mode"),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    if mode == "sync":
        result = await orchestrator.run(request)
        serialized = serialize_state(result)
        return {
            "run_id": request.request_id,
            "status": serialized.get("status", WorkflowStatus.COMPLETED.value),
            "state": serialized,
        }

    run_id = await orchestrator.enqueue(request)
    return {"run_id": run_id, "status": WorkflowStatus.QUEUED.value}


@app.get("/orchestration/runs/{run_id}")
async def get_run_state(
    run_id: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    state = await orchestrator.get_state(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "state": serialize_state(state)}


@app.post("/router/requests")
async def router_start_workflow(
    request: OrchestrationRequest,
    mode: Literal["async", "sync"] = Query(
        "async", description="Execution mode for router-triggered workflows"
    ),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    metadata = dict(request.metadata or {})
    metadata.setdefault("source", "router")
    router_request = request.model_copy(update={"metadata": metadata})

    if mode == "sync":
        result = await orchestrator.run(router_request)
        serialized = serialize_state(result)
        return {
            "run_id": router_request.request_id,
            "status": serialized.get("status", WorkflowStatus.COMPLETED.value),
            "state": serialized,
        }

    run_id = await orchestrator.enqueue(router_request)
    return {
        "run_id": run_id,
        "status": WorkflowStatus.QUEUED.value,
        "metadata": router_request.metadata,
    }


@app.post("/ai/graph/invoke")
async def invoke_ai_graph(
    request: OrchestrationRequest,
    mode: Literal["async", "sync"] = Query("sync", description="Execution mode"),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    """
    Invoke the AI background worker graph directly.

    This endpoint provides direct access to the LangGraph-based AI orchestration pipeline,
    which processes requests through multiple stages:
    - Routing: Determines the appropriate workflow
    - Policy Check: Validates request against configured policies
    - Context Fetching: Retrieves relevant context from memory services
    - Planning: Generates an action plan
    - Reflection: Analyzes the plan
    - Plugin Selection & Dispatch: Executes the planned actions
    - Review: Validates the outcome
    - Memory Update: Persists learned information

    **Execution Modes:**
    - `sync`: Blocks until the graph completes and returns the full state
    - `async`: Enqueues the request and returns immediately with a run_id

    **Example Request (async mode):**
    ```json
    {
        "intent": "send_status_update",
        "channel": "email",
        "audience": {
            "recipients": ["user@example.com"]
        },
        "payload": {
            "template": "Hello {name}!",
            "variables": {"name": "User"}
        }
    }
    ```

    **Response (async mode):**
    ```json
    {
        "run_id": "uuid-string",
        "status": "queued"
    }
    ```

    **Example Request (sync mode):**
    Same as above, but set query parameter `?mode=sync`

    **Response (sync mode):**
    ```json
    {
        "run_id": "uuid-string",
        "status": "completed",
        "state": {
            "request": {...},
            "status": "completed",
            "selected_workflow": "broadcast",
            "policy_decision": {...},
            "planned_actions": [...],
            "analysis_summary": "...",
            "plugin_result": {...},
            "review_feedback": {...},
            "memory_updates": [...]
        }
    }
    ```

    Args:
        request: OrchestrationRequest containing intent, channel, audience, payload, and metadata
        mode: Execution mode - "sync" for immediate execution, "async" for background processing
        orchestrator: Injected AgentOrchestrator dependency

    Returns:
        Dictionary containing run_id, status, and optionally the full state (sync mode)

    Raises:
        HTTPException: 503 if orchestrator is unavailable
        HTTPException: 500 if graph execution fails
    """
    # Add source metadata to track that this came from the AI graph endpoint
    metadata = dict(request.metadata or {})
    metadata.setdefault("source", "ai_graph_invoke")
    graph_request = request.model_copy(update={"metadata": metadata})

    try:
        if mode == "sync":
            # Synchronous execution: run the graph and return the complete state
            logger.info(
                "Invoking AI graph synchronously for request_id=%s, intent=%s",
                graph_request.request_id,
                graph_request.intent,
            )
            result = await orchestrator.run(graph_request)
            serialized = serialize_state(result)
            logger.info(
                "AI graph execution completed for request_id=%s with status=%s",
                graph_request.request_id,
                serialized.get("status"),
            )
            return {
                "run_id": graph_request.request_id,
                "status": serialized.get("status", WorkflowStatus.COMPLETED.value),
                "state": serialized,
            }
        else:
            # Asynchronous execution: enqueue the request and return immediately
            logger.info(
                "Enqueueing AI graph request asynchronously for request_id=%s, intent=%s",
                graph_request.request_id,
                graph_request.intent,
            )
            run_id = await orchestrator.enqueue(graph_request)
            logger.info("AI graph request enqueued with run_id=%s", run_id)
            return {
                "run_id": run_id,
                "status": WorkflowStatus.QUEUED.value,
                "metadata": graph_request.metadata,
            }
    except Exception as exc:
        logger.exception(
            "Failed to invoke AI graph for request_id=%s: %s",
            graph_request.request_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail=f"AI graph invocation failed: {str(exc)}",
        ) from exc
