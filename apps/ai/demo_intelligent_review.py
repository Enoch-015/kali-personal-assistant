#!/usr/bin/env python
"""
Demonstration script showing the intelligent review system in action.

This script demonstrates how the enhanced review system:
1. Categorizes issues intelligently
2. Provides routing context for retries
3. Tracks successful steps
4. Makes recommendations for better replanning
"""

import asyncio

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


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def demo_plugin_failure_detection() -> None:
    """Demonstrate how the sentinel detects and categorizes plugin failures."""
    print_section("Demo 1: Plugin Failure Detection")

    sentinel = get_agent_sentinel()

    state: AgentState = {
        "request": OrchestrationRequest(
            intent="send_email",
            channel="email",
            audience=Audience(recipients=["user1@example.com", "user2@example.com"]),
        ),
        "status": WorkflowStatus.REVIEWING,
        "plugin_result": PluginDispatchResult(
            plugin_name="email-plugin",
            dispatched_count=1,
            failed=["user2@example.com"],
        ),
        "planned_actions": [{"step": 1, "action": "send_email"}],
        "working_notes": [],
        "events": [],
        "requires_human_approval": False,
        "retry_count": 0,
    }

    feedback = sentinel.review(state)

    print(f"\n✓ Workflow Status: {state['status']}")
    print(f"✓ Plugin: {state['plugin_result'].plugin_name}")
    print(f"✓ Success: {state['plugin_result'].dispatched_count}")
    print(f"✓ Failed: {len(state['plugin_result'].failed)}")

    print(f"\n📋 Review Result:")
    print(f"  - Approved: {feedback.approved}")
    print(f"  - Requires Human: {feedback.requires_human}")
    print(f"  - Summary: {feedback.summary}")

    if feedback.detailed_issues:
        print(f"\n🔍 Issues Found ({len(feedback.detailed_issues)}):")
        for issue in feedback.detailed_issues:
            print(f"  • Category: {issue.category.value}")
            print(f"    Description: {issue.description}")
            print(f"    Severity: {issue.severity}")
            print(f"    Actionable: {issue.actionable}")

    if feedback.review_notes:
        print(f"\n📝 Review Notes for Routing Agent:")
        print(f"  - Workflow Stage: {feedback.review_notes.workflow_stage}")
        if feedback.review_notes.recommendations:
            print(f"  - Recommendations:")
            for rec in feedback.review_notes.recommendations:
                print(f"    • {rec}")
        if feedback.review_notes.routing_context:
            print(f"  - Routing Context:")
            for key, value in feedback.review_notes.routing_context.items():
                print(f"    • {key}: {value}")


def demo_intelligent_retry_decision() -> None:
    """Demonstrate how the review agent decides whether to retry."""
    print_section("Demo 2: Intelligent Retry Decision")

    review_agent = get_review_agent()

    # Create a state with actionable issues
    state: AgentState = {
        "request": OrchestrationRequest(intent="test", channel="demo"),
        "status": WorkflowStatus.REVIEWING,
        "working_notes": [],
        "events": [],
        "requires_human_approval": False,
        "retry_count": 0,
    }

    # Add review feedback with actionable issue
    from src.orchestration.models import ReviewFeedback, ReviewIssue, ReviewNotes

    state["review_feedback"] = ReviewFeedback(
        approved=False,
        requires_human=False,
        summary="Plugin delivery failed",
        issues=["Plugin delivery failed"],
        detailed_issues=[
            ReviewIssue(
                category=ReviewIssueCategory.PLUGIN,
                description="Failed to deliver to 1 recipient",
                severity="high",
                actionable=True,
                context={"failed_plugin": "email-plugin"},
            )
        ],
        review_notes=ReviewNotes(
            workflow_stage="reviewing",
            issues_found=[],
            successful_steps=["Context retrieved", "Plan created"],
            recommendations=["Try alternative delivery channel"],
            routing_context={"failed_plugin": "email-plugin"},
        ),
    )

    action, message = review_agent.evaluate(state)

    print(f"\n📊 Review Agent Decision:")
    print(f"  - Action: {action.value}")
    print(f"  - Message: {message}")
    print(f"  - Will Retry: {action.value == 'retry'}")

    if state["review_feedback"].review_notes:
        print(f"\n💡 Context for Retry:")
        notes = state["review_feedback"].review_notes
        if notes.successful_steps:
            print(f"  - Successful Steps: {', '.join(notes.successful_steps)}")
        if notes.recommendations:
            print(f"  - Recommendations: {', '.join(notes.recommendations)}")


def demo_multi_category_issues() -> None:
    """Demonstrate detection of multiple issue categories."""
    print_section("Demo 3: Multi-Category Issue Detection")

    sentinel = get_agent_sentinel()

    state: AgentState = {
        "request": OrchestrationRequest(intent="complex_task", channel="demo"),
        "status": WorkflowStatus.REVIEWING,
        "selected_workflow": "generic-task",
        "planned_actions": [],  # Empty plan
        "retrieved_context": {"memory_snippets": [], "graph_relations": []},  # Low context
        "policy_decision": PolicyDecision(
            allowed=True, requires_human=True, reason="Sensitive operation"
        ),
        "working_notes": [],
        "events": [],
        "requires_human_approval": True,
        "retry_count": 0,
    }

    feedback = sentinel.review(state)

    print(f"\n🔍 Multiple Issues Detected ({len(feedback.detailed_issues)}):")

    # Group issues by category
    by_category = {}
    for issue in feedback.detailed_issues:
        category = issue.category.value
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(issue)

    for category, issues in by_category.items():
        print(f"\n  {category.upper()} Issues ({len(issues)}):")
        for issue in issues:
            print(f"    • {issue.description}")
            print(f"      Severity: {issue.severity}, Actionable: {issue.actionable}")

    if feedback.review_notes:
        print(f"\n📝 Routing Recommendations:")
        for rec in feedback.review_notes.recommendations:
            print(f"  • {rec}")


def main() -> None:
    """Run all demonstrations."""
    print("\n")
    print("=" * 60)
    print(" INTELLIGENT REVIEW SYSTEM DEMONSTRATION")
    print("=" * 60)

    demo_plugin_failure_detection()
    demo_intelligent_retry_decision()
    demo_multi_category_issues()

    print("\n" + "=" * 60)
    print(" Demonstration Complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
