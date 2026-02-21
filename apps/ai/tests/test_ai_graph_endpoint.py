"""Tests for the /ai/graph/invoke endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.orchestration.models import (
    NaturalLanguageGraphRequest,
    OrchestrationRequest,
    PluginDispatchResult,
    PolicyDecision,
    ReviewFeedback,
    WorkflowStatus,
)
from src.services.orchestrator import AgentOrchestrator


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """Create a mock orchestrator for testing."""
    orchestrator = MagicMock(spec=AgentOrchestrator)
    orchestrator.run = AsyncMock()
    orchestrator.enqueue = AsyncMock()
    return orchestrator


@pytest.fixture
def test_client(mock_orchestrator: MagicMock) -> TestClient:
    """Create a test client with mocked orchestrator."""
    app.state.orchestrator = mock_orchestrator
    return TestClient(app)


def test_invoke_ai_graph_sync_mode(test_client: TestClient, mock_orchestrator: MagicMock) -> None:
    """Test AI graph invocation in synchronous mode."""
    # Prepare test data
    request_data = {
        "prompt": "Please send a status update email to user@example.com.",
        "hints": {
            "channel": "email",
            "audience": {"recipients": ["user@example.com"]},
            "payload": {
                "template": "Hello {name}!",
                "variables": {"name": "Test User"},
            },
        },
    }

    # Mock the orchestrator response
    structured_request = OrchestrationRequest(
        intent="send_status_update",
        channel="email",
        audience={"recipients": ["user@example.com"]},
        payload={
            "template": "Hello {name}!",
            "variables": {"name": "Test User"},
        },
        metadata={"source": "ai_graph_invoke"},
    )

    mock_state = {
        "request": structured_request,
        "status": WorkflowStatus.COMPLETED,
        "selected_workflow": "broadcast",
        "policy_decision": PolicyDecision(allowed=True),
        "planned_actions": [{"action": "send_email"}],
        "analysis_summary": "Email sending workflow completed",
        "selected_plugin": "demo-messaging",
        "rendered_message": "Hello Test User!",
        "plugin_result": PluginDispatchResult(
            plugin_name="demo-messaging",
            dispatched_count=1,
        ),
        "review_feedback": ReviewFeedback(approved=True),
        "memory_updates": [],
        "events": [],
        "working_notes": [],
    }
    mock_orchestrator.run.return_value = mock_state

    # Make the request
    response = test_client.post("/ai/graph/invoke?mode=sync", json=request_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "completed"
    assert "state" in data
    assert data["state"]["selected_workflow"] == "broadcast"

    # Verify the orchestrator was called
    mock_orchestrator.run.assert_called_once()
    call_args = mock_orchestrator.run.call_args[0][0]
    assert isinstance(call_args, NaturalLanguageGraphRequest)
    assert call_args.prompt == request_data["prompt"]
    assert call_args.hints is not None
    assert call_args.hints.channel == "email"
    assert call_args.hints.metadata.get("source") == "ai_graph_invoke"


def test_invoke_ai_graph_async_mode(test_client: TestClient, mock_orchestrator: MagicMock) -> None:
    """Test AI graph invocation in asynchronous mode."""
    # Prepare test data
    request_data = {
        "prompt": "Broadcast this update to +15550001111 and +15550002222 on WhatsApp.",
        "hints": {
            "channel": "whatsapp",
            "audience": {"recipients": ["+15550001111", "+15550002222"]},
            "payload": {
                "template": "Broadcast message: {message}",
                "variables": {"message": "Test"},
            },
        },
    }

    # Mock the orchestrator response
    test_run_id = "test-run-id-12345"
    mock_orchestrator.enqueue.return_value = test_run_id

    # Make the request (default mode is async based on endpoint definition)
    response = test_client.post("/ai/graph/invoke?mode=async", json=request_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == test_run_id
    assert data["status"] == "queued"
    assert "metadata" in data
    assert data["metadata"]["source"] == "ai_graph_invoke"

    # Verify the orchestrator was called
    mock_orchestrator.enqueue.assert_called_once()
    call_args = mock_orchestrator.enqueue.call_args[0][0]
    assert isinstance(call_args, NaturalLanguageGraphRequest)
    assert call_args.hints and call_args.hints.channel == "whatsapp"


def test_invoke_ai_graph_default_mode_is_sync(
    test_client: TestClient, mock_orchestrator: MagicMock
) -> None:
    """Test that the default mode for /ai/graph/invoke is sync."""
    request_data = {
        "prompt": "Plan a generic demo task for me.",
        "hints": {"channel": "demo"},
    }

    structured_request = OrchestrationRequest(
        intent="test_intent",
        channel="demo",
        metadata={"source": "ai_graph_invoke"},
    )

    mock_state = {
        "request": structured_request,
        "status": WorkflowStatus.COMPLETED,
        "events": [],
        "working_notes": [],
    }
    mock_orchestrator.run.return_value = mock_state

    # Make request without specifying mode
    response = test_client.post("/ai/graph/invoke", json=request_data)

    # Should use sync mode by default
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    mock_orchestrator.run.assert_called_once()
    call_args = mock_orchestrator.run.call_args[0][0]
    assert isinstance(call_args, NaturalLanguageGraphRequest)
    assert call_args.hints is not None
    assert call_args.hints.metadata["source"] == "ai_graph_invoke"


def test_invoke_ai_graph_with_minimal_request(
    test_client: TestClient, mock_orchestrator: MagicMock
) -> None:
    """Test AI graph invocation with minimal required fields."""
    request_data = {
        "prompt": "Handle this minimal task for me.",
    }

    structured_request = OrchestrationRequest(
        intent="minimal_task",
        metadata={"source": "ai_graph_invoke"},
    )

    mock_state = {
        "request": structured_request,
        "status": WorkflowStatus.COMPLETED,
        "events": [],
        "working_notes": [],
    }
    mock_orchestrator.run.return_value = mock_state

    response = test_client.post("/ai/graph/invoke?mode=sync", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    call_args = mock_orchestrator.run.call_args[0][0]
    assert isinstance(call_args, NaturalLanguageGraphRequest)
    assert call_args.hints is not None
    assert call_args.hints.metadata["source"] == "ai_graph_invoke"


def test_invoke_ai_graph_with_metadata(
    test_client: TestClient, mock_orchestrator: MagicMock
) -> None:
    """Test that custom metadata is preserved and source is added."""
    request_data = {
        "prompt": "Ping user 12345 with session abcde.",
        "hints": {
            "metadata": {
                "user_id": "12345",
                "session_id": "abcde",
            }
        },
    }

    test_run_id = "test-run-id-metadata"
    mock_orchestrator.enqueue.return_value = test_run_id

    response = test_client.post("/ai/graph/invoke?mode=async", json=request_data)

    assert response.status_code == 200

    # Verify metadata is preserved and source is added
    call_args = mock_orchestrator.enqueue.call_args[0][0]
    assert call_args.hints is not None
    assert call_args.hints.metadata["user_id"] == "12345"
    assert call_args.hints.metadata["session_id"] == "abcde"
    assert call_args.hints.metadata["source"] == "ai_graph_invoke"


def test_invoke_ai_graph_orchestrator_unavailable(test_client: TestClient) -> None:
    """Test error handling when orchestrator is not available."""
    # Remove the orchestrator from app state
    app.state.orchestrator = None

    request_data = {
        "prompt": "Test run",
    }

    response = test_client.post("/ai/graph/invoke", json=request_data)

    assert response.status_code == 503
    assert "Orchestrator not available" in response.json()["detail"]


def test_invoke_ai_graph_execution_error(
    test_client: TestClient, mock_orchestrator: MagicMock
) -> None:
    """Test error handling when graph execution fails."""
    request_data = {
        "prompt": "Make this fail",
    }

    # Mock orchestrator to raise an exception
    mock_orchestrator.run.side_effect = RuntimeError("Graph execution failed")

    response = test_client.post("/ai/graph/invoke?mode=sync", json=request_data)

    assert response.status_code == 500
    assert "AI graph invocation failed" in response.json()["detail"]


def test_invoke_ai_graph_invalid_request(test_client: TestClient) -> None:
    """Test error handling for invalid request data."""
    # Missing required 'intent' field
    request_data = {
        "hints": {"channel": "email"},
    }

    response = test_client.post("/ai/graph/invoke", json=request_data)

    assert response.status_code == 422  # Validation error
