import pytest

from src.orchestration import policy
from src.orchestration.models import OrchestrationRequest
from src.orchestration.policy import (
    InMemoryPolicyStore,
    MongoPolicyStore,
    PolicyDirective,
    PolicyStore,
)


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


def test_in_memory_policy_store() -> None:
    """Test InMemoryPolicyStore backend implementation."""
    store = InMemoryPolicyStore()

    # Test empty store
    directives = store.get_directives("test-tenant")
    assert directives == []

    # Add directives
    new_directives = [
        PolicyDirective(directive="never_do", pattern="send spam"),
        PolicyDirective(directive="notify_if", pattern="high priority"),
    ]
    added = store.add_directives("test-tenant", new_directives)
    assert len(added) == 2

    # Verify retrieval
    retrieved = store.get_directives("test-tenant")
    assert len(retrieved) == 2
    assert retrieved[0].pattern == "send spam"
    assert retrieved[1].pattern == "high priority"

    # Test duplicate prevention
    duplicate = [PolicyDirective(directive="never_do", pattern="send spam")]
    added_dup = store.add_directives("test-tenant", duplicate)
    assert len(added_dup) == 0

    # Verify summary
    summary = store.summarize()
    assert summary["backend"] == "memory"
    assert summary["total_directives"] == "2"


def test_mongo_policy_store_fallback() -> None:
    """Test MongoPolicyStore falls back gracefully when MongoDB is unavailable."""
    # Create store with no collection (simulates MongoDB unavailable)
    store = MongoPolicyStore(collection=None)

    # Should still work with caching
    directives = store.get_directives("test-tenant")
    assert directives == []

    # Summary should indicate connection status
    summary = store.summarize()
    assert summary["backend"] == "mongo"
    assert summary["connected"] == "False"


def test_policy_store_facade() -> None:
    """Test PolicyStore facade delegates correctly."""
    # Test with explicit backend
    backend = InMemoryPolicyStore()
    store = PolicyStore(backend=backend)

    # Add directive through facade
    directive = PolicyDirective(directive="never_do", pattern="delete data")
    added = store.add_directives("test-tenant", [directive])
    assert len(added) == 1

    # Retrieve through facade
    retrieved = store.get_directives("test-tenant")
    assert len(retrieved) == 1
    assert retrieved[0].pattern == "delete data"

    # Test summary
    summary = store.summarize()
    assert "backend" in summary
    assert summary["backend"] == "memory"


def test_policy_store_tenant_isolation() -> None:
    """Test that different tenants have isolated policy directives."""
    store = InMemoryPolicyStore()

    # Add directives for tenant A
    tenant_a_directive = PolicyDirective(directive="never_do", pattern="action a")
    store.add_directives("tenant-a", [tenant_a_directive])

    # Add directives for tenant B
    tenant_b_directive = PolicyDirective(directive="never_do", pattern="action b")
    store.add_directives("tenant-b", [tenant_b_directive])

    # Verify isolation
    tenant_a_directives = store.get_directives("tenant-a")
    assert len(tenant_a_directives) == 1
    assert tenant_a_directives[0].pattern == "action a"

    tenant_b_directives = store.get_directives("tenant-b")
    assert len(tenant_b_directives) == 1
    assert tenant_b_directives[0].pattern == "action b"
