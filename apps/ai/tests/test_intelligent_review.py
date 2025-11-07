import pytest

from src.orchestration.models import (
    AgentState,
    Audience,
    OrchestrationRequest,
    PluginDispatchResult,
    PolicyDecision,
    ReviewIssueCategory,
    WorkflowStatus,
)
from src.orchestration.review import get_agent_sentinel, get_review_agent


def test_sentinel_captures_plugin_failure_with_details() -> None:
    """Test that sentinel identifies and categorizes plugin failures intelligently."""
    sentinel = get_agent_sentinel()

    state: AgentState = {
        "request": OrchestrationRequest(
            intent="send_message",
            channel="email",
            audience=Audience(recipients=["user@example.com"]),
        ),
        "status": WorkflowStatus.REVIEWING,
        "plugin_result": PluginDispatchResult(
            plugin_name="email-plugin",
            dispatched_count=0,
            failed=["user@example.com"],
        ),
        "planned_actions": [{"step": 1, "action": "send"}],  # Add planned actions to avoid empty plan issue
        "working_notes": [],
        "events": [],
        "requires_human_approval": False,
        "retry_count": 0,
    }

    feedback = sentinel.review(state)

    assert not feedback.approved
    assert feedback.requires_human
    # Should have at least one plugin-related issue
    plugin_issues = [i for i in feedback.detailed_issues if i.category == ReviewIssueCategory.PLUGIN]
    assert len(plugin_issues) == 1
    assert plugin_issues[0].severity == "high"
    assert plugin_issues[0].actionable
    assert feedback.review_notes is not None
    assert "email-plugin" in feedback.review_notes.routing_context.get("failed_plugin", "")
    assert len(feedback.review_notes.recommendations) > 0


def test_sentinel_identifies_empty_plan() -> None:
    """Test that sentinel detects when no actions are planned."""
    sentinel = get_agent_sentinel()
    
    state: AgentState = {
        "request": OrchestrationRequest(intent="do_something", channel="demo"),
        "status": WorkflowStatus.PLANNING,
        "selected_workflow": "generic-task",
        "planned_actions": [],
        "working_notes": [],
        "events": [],
        "requires_human_approval": False,
        "retry_count": 0,
    }
    
    feedback = sentinel.review(state)
    
    assert len(feedback.detailed_issues) >= 1
    planning_issues = [i for i in feedback.detailed_issues if i.category == ReviewIssueCategory.PLANNING]
    assert len(planning_issues) == 1
    assert "No actions were planned" in planning_issues[0].description


def test_sentinel_tracks_successful_steps() -> None:
    """Test that sentinel records successful workflow steps."""
    sentinel = get_agent_sentinel()
    
    state: AgentState = {
        "request": OrchestrationRequest(intent="test", channel="demo"),
        "status": WorkflowStatus.REVIEWING,
        "selected_workflow": "generic-task",
        "analysis_summary": "Workflow analyzed successfully",
        "planned_actions": [{"step": 1, "action": "test"}],
        "plugin_result": PluginDispatchResult(
            plugin_name="demo-messaging",
            dispatched_count=1,
            failed=[],
        ),
        "policy_decision": PolicyDecision(allowed=True, requires_human=False),
        "working_notes": [],
        "events": [],
        "requires_human_approval": False,
        "retry_count": 0,
    }
    
    feedback = sentinel.review(state)
    
    assert feedback.approved
    assert not feedback.requires_human
    assert feedback.review_notes is None or len(feedback.review_notes.successful_steps) >= 3


def test_sentinel_identifies_policy_constraint() -> None:
    """Test that sentinel properly categorizes policy constraints."""
    sentinel = get_agent_sentinel()
    
    state: AgentState = {
        "request": OrchestrationRequest(intent="sensitive_action", channel="demo"),
        "status": WorkflowStatus.POLICY_CHECK,
        "policy_decision": PolicyDecision(
            allowed=True,
            requires_human=True,
            reason="Sensitive content requires approval",
            tags=["sensitive"],
        ),
        "working_notes": [],
        "events": [],
        "requires_human_approval": True,
        "retry_count": 0,
    }
    
    feedback = sentinel.review(state)
    
    assert not feedback.approved
    assert feedback.requires_human
    policy_issues = [i for i in feedback.detailed_issues if i.category == ReviewIssueCategory.POLICY]
    assert len(policy_issues) == 1
    assert not policy_issues[0].actionable
    assert "routing_context" in (feedback.review_notes.model_dump() if feedback.review_notes else {})


def test_review_agent_uses_detailed_feedback() -> None:
    """Test that review agent leverages detailed issue analysis."""
    review_agent = get_review_agent()
    sentinel = get_agent_sentinel()
    
    state: AgentState = {
        "request": OrchestrationRequest(intent="test", channel="demo"),
        "status": WorkflowStatus.REVIEWING,
        "plugin_result": PluginDispatchResult(
            plugin_name="failing-plugin",
            dispatched_count=0,
            failed=["user1"],
        ),
        "working_notes": [],
        "events": [],
        "requires_human_approval": False,
        "retry_count": 0,
    }
    
    # Get sentinel feedback
    feedback = sentinel.review(state)
    state["review_feedback"] = feedback
    
    # Evaluate with review agent
    action, message = review_agent.evaluate(state)
    
    # Should retry because issues are actionable
    from src.orchestration.models import ReviewAction
    assert action == ReviewAction.RETRY
    assert "retrying workflow" in message.lower()


def test_review_agent_escalates_non_actionable_issues() -> None:
    """Test that review agent doesn't retry for critical non-actionable issues."""
    review_agent = get_review_agent()
    
    from src.orchestration.models import ReviewFeedback, ReviewIssue, ReviewIssueCategory
    
    state: AgentState = {
        "request": OrchestrationRequest(intent="test", channel="demo"),
        "status": WorkflowStatus.REVIEWING,
        "review_feedback": ReviewFeedback(
            approved=False,
            requires_human=True,
            summary="Critical policy violation",
            issues=["Policy blocked"],
            detailed_issues=[
                ReviewIssue(
                    category=ReviewIssueCategory.POLICY,
                    description="Critical security policy violation",
                    severity="critical",
                    actionable=False,
                )
            ],
        ),
        "working_notes": [],
        "events": [],
        "requires_human_approval": True,
        "retry_count": 0,
    }
    
    action, message = review_agent.evaluate(state)
    
    # Should complete (escalate) because issue is non-actionable
    from src.orchestration.models import ReviewAction
    assert action == ReviewAction.COMPLETE
    assert "non-actionable" in message.lower()


def test_sentinel_low_context_detection() -> None:
    """Test that sentinel detects insufficient context."""
    sentinel = get_agent_sentinel()
    
    state: AgentState = {
        "request": OrchestrationRequest(intent="test", channel="demo"),
        "status": WorkflowStatus.FETCHING_CONTEXT,
        "retrieved_context": {"memory_snippets": [], "graph_relations": [], "vector_results": []},
        "working_notes": [],
        "events": [],
        "requires_human_approval": False,
        "retry_count": 0,
    }
    
    feedback = sentinel.review(state)
    
    context_issues = [i for i in feedback.detailed_issues if i.category == ReviewIssueCategory.CONTEXT]
    assert len(context_issues) >= 1
    assert context_issues[0].severity == "low"
    if feedback.review_notes:
        assert feedback.review_notes.routing_context.get("low_context") is True
