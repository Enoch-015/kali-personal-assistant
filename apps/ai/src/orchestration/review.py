from __future__ import annotations

import logging
from functools import lru_cache
from typing import Tuple

from src.config.settings import get_settings

from .models import AgentState, ReviewAction, ReviewFeedback


class AgentSentinel:
    """Performs lightweight governance checks before finalizing a workflow."""

    def review(self, state: AgentState) -> ReviewFeedback:
        notes: list[str] = []
        requires_human = bool(state.get("requires_human_approval"))

        plugin_result = state.get("plugin_result")
        if plugin_result and plugin_result.failed:
            requires_human = True
            notes.append("One or more plugin deliveries failed")

        if state.get("analysis_summary"):
            notes.append("Reflection summary captured")

        policy_decision = state.get("policy_decision")
        if policy_decision and policy_decision.requires_human:
            requires_human = True
            notes.append("Policy requested human approval")

        summary = state.get("rendered_message") or "Workflow completed"

        return ReviewFeedback(
            approved=not requires_human,
            requires_human=requires_human,
            summary=summary,
            issues=notes,
        )


@lru_cache(maxsize=1)
def get_agent_sentinel() -> AgentSentinel:
    return AgentSentinel()


class ReviewAgent:
    """Secondary governance layer that can retry a workflow when issues arise."""

    def __init__(self, max_retries: int | None = None) -> None:
        settings = get_settings()
        configured = max_retries if max_retries is not None else getattr(settings, "review_max_retries", 1)
        self._max_retries = max(0, configured)
        self._logger = logging.getLogger(__name__)

    def evaluate(self, state: AgentState) -> Tuple[ReviewAction, str]:
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

        if not feedback.approved:
            issues = ", ".join(feedback.issues) if feedback.issues else "undisclosed issues"
            if retry_count < self._max_retries:
                message = f"Review agent detected issues ({issues}); retrying workflow"
                self._logger.info(message)
                return ReviewAction.RETRY, message
            message = f"Review agent detected issues ({issues}) after retries; escalating"
            self._logger.warning(message)
            return ReviewAction.COMPLETE, message

        summary = feedback.summary or "Review agent confirms workflow completion"
        self._logger.debug("Review agent approves workflow: %s", summary)
        return ReviewAction.COMPLETE, summary


@lru_cache(maxsize=1)
def get_review_agent() -> ReviewAgent:
    return ReviewAgent()
