from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    ROUTING = "routing"
    POLICY_CHECK = "policy_check"
    FETCHING_CONTEXT = "fetching_context"
    PLANNING = "planning"
    REFLECTING = "reflecting"
    DISPATCHING = "dispatching"
    REVIEWING = "reviewing"
    UPDATING_MEMORY = "updating_memory"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewAction(str, Enum):
    RETRY = "retry"
    COMPLETE = "complete"


class Audience(BaseModel):
    recipients: list[str] = Field(default_factory=list, description="List of recipient IDs")
    segment_id: str | None = Field(
        default=None, description="Optional identifier for a saved recipient segment"
    )

    @field_validator("recipients")
    @classmethod
    def ensure_recipients_present(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one recipient must be provided")
        return value


class OrchestrationRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    intent: str = Field(description="High-level user intent inferred upstream")
    channel: str = Field(
        default="demo",
        description="Requested connector / plugin name (e.g. whatsapp, email, calendar)",
    )
    audience: Audience | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PluginDispatchResult(BaseModel):
    plugin_name: str
    dispatched_count: int
    failed: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    allowed: bool = True
    reason: str = "Request satisfies policy checks"
    requires_human: bool = False
    policy_version: str | None = None
    tags: list[str] = Field(default_factory=list)


class MemorySnapshot(BaseModel):
    memory_snippets: list[str] = Field(default_factory=list)
    graph_relations: list[str] = Field(default_factory=list)
    vector_results: list[str] = Field(default_factory=list)
    freshness_seconds: int = 0


class MemoryUpdate(BaseModel):
    summary: str
    annotations: dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0


class ReviewIssueCategory(str, Enum):
    """Categories for issues identified during review."""
    POLICY = "policy"
    PLUGIN = "plugin"
    CONTEXT = "context"
    PLANNING = "planning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    OTHER = "other"


class ReviewIssue(BaseModel):
    """Detailed issue identified during review."""
    category: ReviewIssueCategory
    description: str
    severity: str = Field(default="medium", description="low, medium, high, critical")
    context: dict[str, Any] = Field(default_factory=dict)
    actionable: bool = Field(default=True, description="Whether issue can be addressed by retry")


class ReviewNotes(BaseModel):
    """Detailed notes from review for routing agent consumption."""
    workflow_stage: str = Field(description="Stage where review occurred")
    issues_found: list[ReviewIssue] = Field(default_factory=list)
    successful_steps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    routing_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context to help routing agent make better decisions on retry"
    )


class ReviewFeedback(BaseModel):
    approved: bool = True
    requires_human: bool = False
    summary: str = ""
    issues: list[str] = Field(default_factory=list)
    detailed_issues: list[ReviewIssue] = Field(
        default_factory=list,
        description="Categorized issues for intelligent review"
    )
    review_notes: ReviewNotes | None = Field(
        default=None,
        description="Detailed notes for routing agent on failure"
    )


class AgentEvent(BaseModel):
    type: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentState(TypedDict, total=False):
    request: OrchestrationRequest
    status: WorkflowStatus
    selected_workflow: str
    policy_decision: PolicyDecision
    working_notes: list[str]
    retrieved_context: dict[str, Any]
    context_validation: dict[str, Any]
    planned_actions: list[dict[str, Any]]
    analysis_summary: str
    selected_plugin: str
    rendered_message: str | None
    plugin_result: PluginDispatchResult
    review_feedback: ReviewFeedback
    memory_updates: list[MemoryUpdate]
    requires_human_approval: bool
    events: list[AgentEvent]
    error: str
    captured_policy_directives: list[dict[str, str]]
    retry_count: int
    review_action: ReviewAction
    review_agent_message: str


def new_initial_state(request: OrchestrationRequest) -> AgentState:
    return {
        "request": request,
        "status": WorkflowStatus.QUEUED,
        "working_notes": [],
        "events": [],
        "requires_human_approval": False,
        "retry_count": 0,
    }
