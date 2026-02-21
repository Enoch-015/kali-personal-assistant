"""Integration test demonstrating intelligent review and retry with routing context."""

import pytest

from src.orchestration.graph import build_langgraph
from src.orchestration.models import Audience, OrchestrationRequest, PluginDispatchResult
from src.orchestration.plugins.base import BasePlugin, registry


class FailOnceThenSucceedPlugin(BasePlugin):
    """Test plugin that fails on first attempt but succeeds on retry."""

    def __init__(self) -> None:
        self.name = "fail-once-plugin"
        self.attempt_count = 0

    async def dispatch(
        self, request: OrchestrationRequest, rendered: str
    ) -> PluginDispatchResult:
        """Fail on first attempt, succeed on retry."""
        self.attempt_count += 1

        if self.attempt_count == 1:
            # First attempt fails
            return PluginDispatchResult(
                plugin_name=self.name,
                dispatched_count=0,
                failed=request.audience.recipients if request.audience else [],
                metadata={"attempt": self.attempt_count, "status": "failed"},
            )
        else:
            # Subsequent attempts succeed
            recipient_count = len(request.audience.recipients) if request.audience else 0
            return PluginDispatchResult(
                plugin_name=self.name,
                dispatched_count=recipient_count,
                failed=[],
                metadata={"attempt": self.attempt_count, "status": "success"},
            )


@pytest.mark.asyncio
async def test_intelligent_review_with_retry_and_routing_context() -> None:
    """Test that review system provides context to routing agent for better retry decisions."""

    # Register the test plugin
    plugin = FailOnceThenSucceedPlugin()
    registry.register(plugin)

    graph = build_langgraph()
    request = OrchestrationRequest(
        intent="send_important_message",
        channel="fail-once-plugin",
        audience=Audience(recipients=["+15550001111", "+15550002222"]),
        payload={"template": "Important: {message}", "variables": {"message": "Test"}},
        metadata={"plugin": "fail-once-plugin"},
    )

    result = await graph.ainvoke(
        {"request": request},
        config={"configurable": {"thread_id": request.request_id}},
    )

    # Verify the workflow completed successfully after retry
    from src.orchestration.models import WorkflowStatus

    assert result["status"] == WorkflowStatus.COMPLETED

    # Verify retry occurred
    assert result.get("retry_count", 0) > 0, "Should have retried at least once"

    # Verify review feedback was generated on first attempt
    review_feedback = result.get("review_feedback")
    assert review_feedback is not None

    # On retry, should have succeeded
    plugin_result = result.get("plugin_result")
    assert plugin_result is not None
    assert plugin_result.dispatched_count == 2
    assert len(plugin_result.failed) == 0

    # Verify working notes captured retry context
    working_notes = result.get("working_notes", [])
    assert len(working_notes) > 0

    # Should have notes about retry and previous attempt
    retry_notes = [note for note in working_notes if "Retry" in note or "retry" in note]
    assert len(retry_notes) > 0, "Should have notes about retry attempt"

    # Events should show retry workflow
    events = result.get("events", [])
    review_events = [e for e in events if e.type == "review.agent"]
    assert len(review_events) > 0, "Should have review agent events"


@pytest.mark.asyncio
async def test_review_notes_passed_to_routing_agent() -> None:
    """Test that review notes with routing context are accessible for routing decisions."""

    # Use a different instance for this test
    plugin2 = FailOnceThenSucceedPlugin()
    plugin2.name = "fail-once-plugin-2"
    registry.register(plugin2)

    graph = build_langgraph()
    request = OrchestrationRequest(
        intent="broadcast_update",
        channel="fail-once-plugin-2",
        audience=Audience(recipients=["+15550003333"]),
        metadata={"plugin": "fail-once-plugin-2"},
    )

    result = await graph.ainvoke(
        {"request": request},
        config={"configurable": {"thread_id": request.request_id}},
    )

    # After retry, check if routing context was used
    working_notes = result.get("working_notes", [])

    # The working notes should include context from the review
    # Look for notes that mention issues, recommendations, or successful steps
    context_notes = [
        note
        for note in working_notes
        if any(
            keyword in note.lower()
            for keyword in ["retry", "previous", "successful", "issue", "recommendation"]
        )
    ]

    # Should have some context notes if retry occurred
    if result.get("retry_count", 0) > 0:
        assert (
            len(context_notes) > 0
        ), "Should have routing context in notes after retry"
