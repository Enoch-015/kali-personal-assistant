from __future__ import annotations

from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from .models import (
    AgentEvent,
    AgentState,
    MemoryUpdate,
    OrchestrationRequest,
    PolicyDecision,
    PluginDispatchResult,
    ReviewFeedback,
    WorkflowStatus,
)
from .memory import get_memory_service
from .policy import get_policy_engine
from .plugins.base import registry
from .review import get_agent_sentinel


def _require_request(state: AgentState) -> OrchestrationRequest:
    request = state.get("request")
    if request is None:
        raise ValueError("Agent state missing 'request'")
    return request


def _with_event(state: AgentState, event: AgentEvent) -> List[AgentEvent]:
    existing = list(state.get("events") or [])
    existing.append(event)
    return existing


async def route_request(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    workflow = request.metadata.get("workflow")
    if not workflow:
        workflow = "broadcast" if request.audience else "generic-task"

    note = f"Routed intent '{request.intent}' to workflow '{workflow}'"
    notes = list(state.get("working_notes") or [])
    notes.append(note)

    event = AgentEvent(
        type="router.decision",
        message=note,
        data={"request_id": request.request_id, "channel": request.channel},
    )
    return {
        "status": WorkflowStatus.ROUTING,
        "selected_workflow": workflow,
        "working_notes": notes,
        "events": _with_event(state, event),
    }


async def policy_check(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    policy_engine = get_policy_engine()
    decision: PolicyDecision = policy_engine.evaluate(request)
    notes = list(state.get("working_notes") or [])
    note = f"Policy decision: {decision.reason}"
    notes.append(note)

    event = AgentEvent(
        type="policy.review",
        message=note,
        data={
            "allowed": decision.allowed,
            "requires_human": decision.requires_human,
            "policy_version": decision.policy_version,
        },
    )
    if not decision.allowed:
        raise PermissionError(decision.reason)

    return {
        "status": WorkflowStatus.POLICY_CHECK,
        "policy_decision": decision,
        "requires_human_approval": decision.requires_human or state.get("requires_human_approval", False),
        "working_notes": notes,
        "events": _with_event(state, event),
    }


async def fetch_context(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    memory_service = get_memory_service()
    snapshot = memory_service.retrieve_context(request)
    validation = memory_service.validate_relevance(snapshot, request.intent)
    notes = list(state.get("working_notes") or [])
    notes.append("Context hydrated from memory layer placeholder")

    event = AgentEvent(
        type="context.fetched",
        message="Fetched contextual signals from memory layer",
        data={
            "snippets": len(snapshot.memory_snippets),
            "graph_relations": len(snapshot.graph_relations),
            "validation": validation.get("summary"),
        },
    )
    return {
        "status": WorkflowStatus.FETCHING_CONTEXT,
        "retrieved_context": snapshot.model_dump(),
        "context_validation": validation,
        "working_notes": notes,
        "events": _with_event(state, event),
    }


def plan_actions(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    workflow = state.get("selected_workflow", "generic-task")
    plan = [
        {"step": 1, "action": "analyse_intent", "details": request.intent},
        {"step": 2, "action": "prepare_tool_invocation", "details": workflow},
    ]
    event = AgentEvent(
        type="planner.plan_created",
        message="Created high-level plan",
        data={"steps": len(plan)},
    )
    return {
        "status": WorkflowStatus.PLANNING,
        "planned_actions": plan,
        "events": _with_event(state, event),
    }


def agent_reflection(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    context = state.get("retrieved_context", {})
    plan = state.get("planned_actions", [])

    summary_parts = [
        f"Intent: {request.intent}",
        f"Planned steps: {len(plan)}",
        f"Context snippets: {len(context.get('memory_snippets', []))}",
    ]
    context_validation = state.get("context_validation")
    if context_validation:
        summary_parts.append(context_validation.get("summary", ""))
    reflection = " | ".join(part for part in summary_parts if part)

    event = AgentEvent(
        type="agent.reflect",
        message="Generated reasoning summary",
        data={"summary": reflection},
    )

    return {
        "status": WorkflowStatus.REFLECTING,
        "analysis_summary": reflection,
        "events": _with_event(state, event),
    }


def select_plugin(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    workflow = state.get("selected_workflow", "generic-task")
    preferred = request.metadata.get("plugin") if request.metadata else None

    candidate = preferred or request.channel or "demo-messaging"
    if workflow == "generic-task":
        candidate = preferred or "demo-messaging"

    notes = list(state.get("working_notes") or [])
    notes.append(f"Selected plugin candidate '{candidate}'")

    event = AgentEvent(
        type="plugin.selected",
        message=f"Candidate plugin '{candidate}' chosen",
        data={"preferred": preferred, "channel": request.channel},
    )
    return {
        "selected_plugin": candidate,
        "working_notes": notes,
        "events": _with_event(state, event),
    }


def render_payload(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    payload = request.payload or {}
    template = payload.get("template") or "[demo] {intent}"
    variables = {"intent": request.intent, **payload.get("variables", {})}
    try:
        rendered = template.format(**variables)
    except KeyError:
        rendered = f"{template} | vars={variables}"

    event = AgentEvent(
        type="message.rendered",
        message="Rendered payload for plugin dispatch",
        data={"char_count": len(rendered)},
    )
    return {
        "rendered_message": rendered,
        "events": _with_event(state, event),
    }


async def execute_plugin(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    plugin_name = state.get("selected_plugin")
    plugin = registry.get(plugin_name) if plugin_name else None
    if plugin is None:
        raise RuntimeError(f"No plugin registered under name '{plugin_name}'")

    rendered = state.get("rendered_message") or ""
    result: PluginDispatchResult = await plugin.dispatch(request, rendered)
    event = AgentEvent(
        type="plugin.dispatched",
        message=f"Plugin '{result.plugin_name}' dispatched",
        data={"dispatched_count": result.dispatched_count},
    )
    return {
        "status": WorkflowStatus.DISPATCHING,
        "plugin_result": result,
        "events": _with_event(state, event),
    }


def review_outcome(state: AgentState) -> Dict[str, Any]:
    sentinel = get_agent_sentinel()
    feedback: ReviewFeedback = sentinel.review(state)
    notes = list(state.get("working_notes") or [])
    notes.append("Sentinel review complete")

    event = AgentEvent(
        type="agent.review",
        message="Agent sentinel produced final decision",
        data={
            "approved": feedback.approved,
            "requires_human": feedback.requires_human,
            "issues": feedback.issues,
        },
    )

    return {
        "status": WorkflowStatus.REVIEWING,
        "review_feedback": feedback,
        "requires_human_approval": feedback.requires_human or state.get("requires_human_approval", False),
        "working_notes": notes,
        "events": _with_event(state, event),
    }


def update_memory(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    memory_service = get_memory_service()
    plugin_result: PluginDispatchResult | None = state.get("plugin_result")
    reflection: str = state.get("analysis_summary", "")
    updates: List[MemoryUpdate] = memory_service.prepare_updates(request, plugin_result, reflection)

    event = AgentEvent(
        type="memory.updated",
        message="Prepared memory updates",
        data={"entries": len(updates)},
    )

    return {
        "status": WorkflowStatus.UPDATING_MEMORY,
        "memory_updates": updates,
        "events": _with_event(state, event),
    }


def finalize(state: AgentState) -> Dict[str, Any]:
    request = _require_request(state)
    event = AgentEvent(
        type="workflow.completed",
        message="Workflow completed successfully",
        data={"request_id": request.request_id},
    )
    return {
        "status": WorkflowStatus.COMPLETED,
        "requires_human_approval": state.get("requires_human_approval", False),
        "events": _with_event(state, event),
    }


def _plugin_route(state: AgentState) -> str:
    return "dispatch" if state.get("selected_plugin") else "skip"


def build_langgraph(checkpointer: Optional[InMemorySaver] = None) -> Any:
    builder = StateGraph(AgentState)
    builder.add_node("route_request", route_request)
    builder.add_node("policy_check", policy_check)
    builder.add_node("fetch_context", fetch_context)
    builder.add_node("plan_actions", plan_actions)
    builder.add_node("agent_reflection", agent_reflection)
    builder.add_node("select_plugin", select_plugin)
    builder.add_node("render_payload", render_payload)
    builder.add_node("execute_plugin", execute_plugin)
    builder.add_node("review_outcome", review_outcome)
    builder.add_node("update_memory", update_memory)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "route_request")
    builder.add_edge("route_request", "policy_check")
    builder.add_edge("policy_check", "fetch_context")
    builder.add_edge("fetch_context", "plan_actions")
    builder.add_edge("plan_actions", "agent_reflection")
    builder.add_edge("agent_reflection", "select_plugin")
    builder.add_edge("select_plugin", "render_payload")
    builder.add_conditional_edges(
        "render_payload",
        _plugin_route,
        {
            "dispatch": "execute_plugin",
            "skip": "review_outcome",
        },
    )
    builder.add_edge("execute_plugin", "review_outcome")
    builder.add_edge("review_outcome", "update_memory")
    builder.add_edge("update_memory", "finalize")
    builder.add_edge("finalize", END)

    checkpointer = checkpointer or InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
