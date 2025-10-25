import pytest

from src.orchestration.models import OrchestrationRequest
from src.orchestration import policy


@pytest.fixture(autouse=True)
def reset_policy_cache() -> None:
    policy.get_policy_engine.cache_clear()
    policy.get_policy_feedback_agent.cache_clear()
    policy._get_policy_store.cache_clear()  # type: ignore[attr-defined]
    yield
    policy.get_policy_engine.cache_clear()
    policy.get_policy_feedback_agent.cache_clear()
    policy._get_policy_store.cache_clear()  # type: ignore[attr-defined]


def test_policy_agent_captures_and_blocks() -> None:
    agent = policy.get_policy_feedback_agent()
    capture_request = OrchestrationRequest(
        intent="configure_policies",
        channel="cli",
        metadata={
            "tenant_id": "tenant-123",
            "policy_feedback": [
                "Never do marketing blasts",
                "Tell me if escalation",
            ],
        },
    )

    captured = agent.capture(capture_request)
    assert len(captured) == 2

    engine = policy.get_policy_engine()

    deny_request = OrchestrationRequest(
        intent="Marketing blasts for new product",
        channel="email",
        metadata={"tenant_id": "tenant-123"},
        payload={"message": "Launch marketing blasts"},
    )

    deny_decision = engine.evaluate(deny_request)
    assert not deny_decision.allowed
    assert deny_decision.requires_human
    assert any(tag.startswith("policy:block") or tag == "policy:block" for tag in deny_decision.tags)

    notify_request = OrchestrationRequest(
        intent="Escalation report",
        channel="email",
        metadata={"tenant_id": "tenant-123"},
    )

    notify_decision = engine.evaluate(notify_request)
    assert notify_decision.allowed
    assert notify_decision.requires_human
    assert "policy:notify" in notify_decision.tags


def test_policy_agent_ignores_duplicate_feedback() -> None:
    agent = policy.get_policy_feedback_agent()
    request = OrchestrationRequest(
        intent="configure_policies",
        channel="cli",
        metadata={
            "tenant_id": "tenant-abc",
            "policy_feedback": "Never do duplicate submissions",
        },
    )

    first_capture = agent.capture(request)
    assert len(first_capture) == 1

    second_capture = agent.capture(request)
    assert second_capture == []

    engine = policy.get_policy_engine()
    decision = engine.evaluate(
        OrchestrationRequest(
            intent="Duplicate submissions",
            channel="email",
            metadata={"tenant_id": "tenant-abc"},
        )
    )
    assert not decision.allowed
    assert decision.requires_human
