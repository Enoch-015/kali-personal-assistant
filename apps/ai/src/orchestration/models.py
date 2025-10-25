from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict
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
    recipients: List[str] = Field(default_factory=list, description="List of recipient IDs")
    segment_id: Optional[str] = Field(
        default=None, description="Optional identifier for a saved recipient segment"
    )

    @field_validator("recipients")
    @classmethod
    def ensure_recipients_present(cls, value: List[str]) -> List[str]:
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
    audience: Optional[Audience] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PluginDispatchResult(BaseModel):
    plugin_name: str
    dispatched_count: int
    failed: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    allowed: bool = True
    reason: str = "Request satisfies policy checks"
    requires_human: bool = False
    policy_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class MemorySnapshot(BaseModel):
    memory_snippets: List[str] = Field(default_factory=list)
    graph_relations: List[str] = Field(default_factory=list)
    vector_results: List[str] = Field(default_factory=list)
    freshness_seconds: int = 0


class MemoryUpdate(BaseModel):
    summary: str
    annotations: Dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0


class ReviewFeedback(BaseModel):
    approved: bool = True
    requires_human: bool = False
    summary: str = ""
    issues: List[str] = Field(default_factory=list)


class AgentEvent(BaseModel):
    type: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


class AgentState(TypedDict, total=False):
    request: OrchestrationRequest
    status: WorkflowStatus
    selected_workflow: str
    policy_decision: PolicyDecision
    working_notes: List[str]
    retrieved_context: Dict[str, Any]
    context_validation: Dict[str, Any]
    planned_actions: List[Dict[str, Any]]
    analysis_summary: str
    selected_plugin: str
    rendered_message: Optional[str]
    plugin_result: PluginDispatchResult
    review_feedback: ReviewFeedback
    memory_updates: List[MemoryUpdate]
    requires_human_approval: bool
    events: List[AgentEvent]
    error: str
    captured_policy_directives: List[Dict[str, str]]
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
