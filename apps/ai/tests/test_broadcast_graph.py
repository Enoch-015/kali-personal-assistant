import pytest

from src.orchestration.graph import build_langgraph
from src.orchestration.models import Audience, OrchestrationRequest, WorkflowStatus
from src.orchestration.plugins.demo import register_demo_plugin
from src.orchestration.plugins.resend_email import register_resend_plugin


@pytest.mark.asyncio
async def test_langgraph_handles_generic_task_without_audience() -> None:
    register_demo_plugin()
    register_resend_plugin()
    graph = build_langgraph()
    request = OrchestrationRequest(
        intent="summarize_notes",
        channel="",
        audience=None,
        payload={"template": "Task: {intent}"},
    )

    result = await graph.ainvoke(
        {"request": request},
        config={"configurable": {"thread_id": request.request_id}},
    )

    assert result["status"] == WorkflowStatus.COMPLETED
    assert result["rendered_message"] == "Task: summarize_notes"
    assert result["selected_workflow"] == "generic-task"
    assert result.get("policy_decision") is not None
    assert result.get("review_feedback") is not None
    assert result.get("requires_human_approval") is False