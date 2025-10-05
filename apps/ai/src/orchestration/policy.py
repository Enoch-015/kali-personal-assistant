from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional

from .models import OrchestrationRequest, PolicyDecision


class PolicyEngine:
    """Simple policy engine placeholder.

    In a full implementation this would evaluate tenant-specific rules,
    safety filters, throttling, and escalation policies. For now it focuses on
    shaping metadata so downstream nodes can react accordingly.
    """

    def __init__(self, policy_version: Optional[str] = None) -> None:
        self._policy_version = policy_version or "demo/v1"

    def evaluate(self, request: OrchestrationRequest) -> PolicyDecision:
        tags: list[str] = []
        requires_human = False

        intent = request.intent.lower()
        if intent.startswith("escalate"):
            requires_human = True
            tags.append("escalation")

        if request.metadata.get("priority") == "high":
            tags.append("priority:high")

        reason = "Policy check passed"
        if requires_human:
            reason = "Requires human review before dispatch"

        return PolicyDecision(
            allowed=True,
            requires_human=requires_human,
            reason=reason,
            policy_version=self._policy_version,
            tags=tags,
        )

    def summarize(self) -> Dict[str, str]:
        return {"policy_version": self._policy_version}


@lru_cache(maxsize=1)
def get_policy_engine() -> PolicyEngine:
    return PolicyEngine()
