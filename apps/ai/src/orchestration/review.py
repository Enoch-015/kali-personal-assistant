from __future__ import annotations

from functools import lru_cache

from .models import AgentState, ReviewFeedback


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
