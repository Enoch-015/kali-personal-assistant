import pytest

from src.orchestration.graph import build_langgraph
from src.orchestration.models import Audience, OrchestrationRequest, WorkflowStatus
from src.orchestration.plugins.demo import register_demo_plugin


@pytest.mark.asyncio
async def test_langgraph_executes_demo_plugin() -> None:
    register_demo_plugin()
    graph = build_langgraph()
    request = OrchestrationRequest(
        intent="send_broadcast",
        channel="whatsapp",
        audience=Audience(recipients=["+15550001111"]),
        payload={"template": "Hello {name}", "variables": {"name": "Kali"}},
    )

    result = await graph.ainvoke(
        {"request": request},
        config={"configurable": {"thread_id": request.request_id}},
    )

    assert result["status"] == WorkflowStatus.COMPLETED
    assert request.request_id == result["request"].request_id
    assert result.get("rendered_message") == "Hello Kali"
    plugin_result = result.get("plugin_result")
    assert plugin_result is not None
    assert plugin_result.dispatched_count == 1
    assert plugin_result.plugin_name == "demo-messaging"
    policy = result.get("policy_decision")
    assert policy is not None and policy.allowed
    assert bool(result.get("analysis_summary"))
    review = result.get("review_feedback")
    assert review is not None and review.approved
    updates = result.get("memory_updates")
    assert updates is not None and len(updates) == 1
