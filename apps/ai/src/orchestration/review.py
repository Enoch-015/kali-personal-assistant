from __future__ import annotations

import logging
from functools import lru_cache

from src.config.settings import get_settings

from .models import (
    AgentState,
    ReviewAction,
    ReviewFeedback,
    ReviewIssue,
    ReviewIssueCategory,
    ReviewNotes,
)


class AgentSentinel:
    """Performs intelligent governance checks before finalizing a workflow."""

    def review(self, state: AgentState) -> ReviewFeedback:
        """Intelligently review workflow state and categorize issues for routing agent."""
        notes: list[str] = []
        detailed_issues: list[ReviewIssue] = []
        successful_steps: list[str] = []
        recommendations: list[str] = []
        routing_context: dict = {}
        requires_human = bool(state.get("requires_human_approval"))

        # Determine current workflow stage
        workflow_stage = str(state.get("status", "unknown"))

        # Review plugin execution
        plugin_result = state.get("plugin_result")
        if plugin_result:
            if plugin_result.failed:
                requires_human = True
                notes.append("One or more plugin deliveries failed")
                detailed_issues.append(ReviewIssue(
                    category=ReviewIssueCategory.PLUGIN,
                    description=f"Plugin delivery failed for {len(plugin_result.failed)} recipient(s)",
                    severity="high",
                    context={
                        "plugin_name": plugin_result.plugin_name,
                        "failed_count": len(plugin_result.failed),
                        "failed_recipients": plugin_result.failed
                    },
                    actionable=True
                ))
                recommendations.append("Consider retrying with different delivery channel")
                routing_context["failed_plugin"] = plugin_result.plugin_name
                routing_context["failed_recipients"] = plugin_result.failed
            else:
                successful_steps.append(f"Plugin {plugin_result.plugin_name} executed successfully")

        # Review analysis and planning
        if state.get("analysis_summary"):
            notes.append("Reflection summary captured")
            successful_steps.append("Agent reflection completed")

        planned_actions = state.get("planned_actions", [])
        if not planned_actions or len(planned_actions) == 0:
            detailed_issues.append(ReviewIssue(
                category=ReviewIssueCategory.PLANNING,
                description="No actions were planned for execution",
                severity="medium",
                context={"workflow": state.get("selected_workflow", "unknown")},
                actionable=True
            ))
            recommendations.append("Review workflow selection and planning logic")
            routing_context["empty_plan"] = True

        # Review policy decisions
        policy_decision = state.get("policy_decision")
        if policy_decision:
            if policy_decision.requires_human:
                requires_human = True
                notes.append("Policy requested human approval")
                detailed_issues.append(ReviewIssue(
                    category=ReviewIssueCategory.POLICY,
                    description=f"Policy requires human approval: {policy_decision.reason}",
                    severity="high",
                    context={
                        "policy_reason": policy_decision.reason,
                        "policy_version": policy_decision.policy_version,
                        "tags": policy_decision.tags
                    },
                    actionable=False
                ))
                routing_context["policy_blocked"] = True
                routing_context["policy_reason"] = policy_decision.reason
            elif not policy_decision.allowed:
                requires_human = True
                detailed_issues.append(ReviewIssue(
                    category=ReviewIssueCategory.POLICY,
                    description=f"Policy check failed: {policy_decision.reason}",
                    severity="critical",
                    context={"policy_reason": policy_decision.reason},
                    actionable=False
                ))
            else:
                successful_steps.append("Policy validation passed")

        # Review context fetching
        retrieved_context = state.get("retrieved_context")
        context_validation = state.get("context_validation")
        if retrieved_context:
            snippet_count = len(retrieved_context.get("memory_snippets", []))
            if snippet_count == 0:
                detailed_issues.append(ReviewIssue(
                    category=ReviewIssueCategory.CONTEXT,
                    description="No relevant context retrieved from memory",
                    severity="low",
                    context={"memory_provider": "unknown"},
                    actionable=True
                ))
                recommendations.append("Consider enriching memory with more relevant information")
                routing_context["low_context"] = True
            else:
                successful_steps.append(f"Retrieved {snippet_count} relevant memory snippets")

        # Check for validation issues
        if context_validation:
            validation_summary = context_validation.get("summary", "")
            if "insufficient" in validation_summary.lower() or "irrelevant" in validation_summary.lower():
                detailed_issues.append(ReviewIssue(
                    category=ReviewIssueCategory.VALIDATION,
                    description="Context validation indicates insufficient or irrelevant information",
                    severity="medium",
                    context={"validation": validation_summary},
                    actionable=True
                ))
                recommendations.append("Refine context retrieval strategy")

        # Review workflow selection
        selected_workflow = state.get("selected_workflow")
        if selected_workflow:
            successful_steps.append(f"Workflow '{selected_workflow}' selected")
            routing_context["workflow"] = selected_workflow

        # Check for errors
        error = state.get("error")
        if error:
            requires_human = True
            detailed_issues.append(ReviewIssue(
                category=ReviewIssueCategory.EXECUTION,
                description=f"Execution error: {error}",
                severity="critical",
                context={"error": error},
                actionable=True
            ))
            routing_context["execution_error"] = error

        # Generate summary
        summary = state.get("rendered_message") or "Workflow completed"
        if detailed_issues:
            high_severity_count = sum(1 for issue in detailed_issues if issue.severity in ["high", "critical"])
            if high_severity_count > 0:
                summary = f"Workflow completed with {high_severity_count} critical issue(s)"

        # Build review notes for routing agent
        review_notes = ReviewNotes(
            workflow_stage=workflow_stage,
            issues_found=detailed_issues,
            successful_steps=successful_steps,
            recommendations=recommendations,
            routing_context=routing_context
        ) if detailed_issues or routing_context else None

        return ReviewFeedback(
            approved=not requires_human,
            requires_human=requires_human,
            summary=summary,
            issues=notes,
            detailed_issues=detailed_issues,
            review_notes=review_notes,
        )


@lru_cache(maxsize=1)
def get_agent_sentinel() -> AgentSentinel:
    return AgentSentinel()


class ReviewAgent:
    """Enhanced governance layer that intelligently evaluates failures and provides context for replanning."""

    def __init__(self, max_retries: int | None = None) -> None:
        settings = get_settings()
        configured = max_retries if max_retries is not None else getattr(settings, "review_max_retries", 1)
        self._max_retries = max(0, configured)
        self._logger = logging.getLogger(__name__)

    def evaluate(self, state: AgentState) -> tuple[ReviewAction, str]:
        """Evaluate workflow state and decide whether to retry or complete.

        Provides intelligent feedback that the routing agent can use to create better plans on retry.
        """
        retry_count = int(state.get("retry_count") or 0)
        feedback: ReviewFeedback | None = state.get("review_feedback")

        if feedback is None:
            if retry_count < self._max_retries:
                message = "Review agent missing feedback; retrying workflow"
                self._logger.info(message)
                return ReviewAction.RETRY, message
            message = "Review agent missing feedback; escalating for review"
            self._logger.warning(message)
            return ReviewAction.COMPLETE, message

        # Analyze detailed issues if available
        if feedback.detailed_issues:
            actionable_issues = [
                issue for issue in feedback.detailed_issues
                if issue.actionable and issue.severity in ["medium", "high", "critical"]
            ]
            non_actionable_issues = [
                issue for issue in feedback.detailed_issues
                if not issue.actionable
            ]

            # Log insights about the issues for observability
            if actionable_issues:
                categories = {issue.category.value for issue in actionable_issues}
                self._logger.info(
                    "Found %d actionable issues in categories: %s",
                    len(actionable_issues),
                    ", ".join(categories)
                )

            # If we have non-actionable issues, don't retry
            if non_actionable_issues and not feedback.approved:
                critical_non_actionable = [
                    issue for issue in non_actionable_issues
                    if issue.severity == "critical"
                ]
                if critical_non_actionable:
                    issue_desc = "; ".join(issue.description for issue in critical_non_actionable)
                    message = f"Critical non-actionable issues detected: {issue_desc}"
                    self._logger.warning(message)
                    return ReviewAction.COMPLETE, message

        if not feedback.approved:
            issues = ", ".join(feedback.issues) if feedback.issues else "undisclosed issues"

            # Provide context for routing agent
            context_msg = ""
            if feedback.review_notes and feedback.review_notes.recommendations:
                context_msg = f" Recommendations: {'; '.join(feedback.review_notes.recommendations[:2])}"

            if retry_count < self._max_retries:
                message = f"Review agent detected issues ({issues}); retrying workflow{context_msg}"
                self._logger.info(message)

                # Log routing context for observability
                if feedback.review_notes and feedback.review_notes.routing_context:
                    self._logger.debug(
                        "Routing context for retry: %s",
                        feedback.review_notes.routing_context
                    )

                return ReviewAction.RETRY, message

            message = f"Review agent detected issues ({issues}) after retries; escalating{context_msg}"
            self._logger.warning(message)
            return ReviewAction.COMPLETE, message

        summary = feedback.summary or "Review agent confirms workflow completion"

        # Log successful review with context
        if feedback.review_notes and feedback.review_notes.successful_steps:
            self._logger.debug(
                "Workflow completed successfully with steps: %s",
                ", ".join(feedback.review_notes.successful_steps[:3])
            )

        self._logger.debug("Review agent approves workflow: %s", summary)
        return ReviewAction.COMPLETE, summary


@lru_cache(maxsize=1)
def get_review_agent() -> ReviewAgent:
    return ReviewAgent()
