from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from .memory import get_memory_service
from .models import (
    AgentEvent,
    AgentState,
    MemoryUpdate,
    OrchestrationRequest,
    PluginDispatchResult,
    PolicyDecision,
    ReviewAction,
    ReviewFeedback,
    WorkflowStatus,
)
from .plugins.base import registry
from .policy import get_policy_engine, get_policy_feedback_agent
from .reasoning import get_reasoning_agent
from .review import get_agent_sentinel, get_review_agent


def _require_request(state: AgentState) -> OrchestrationRequest:
    request = state.get("request")
    if request is None:
        raise ValueError("Agent state missing 'request'")
    return request


def _with_event(state: AgentState, event: AgentEvent) -> list[AgentEvent]:
    existing = list(state.get("events") or [])
    existing.append(event)
    return existing


def _review_route(state: AgentState) -> ReviewAction:
    action = state.get("review_action")
    if isinstance(action, ReviewAction):
        return action
    if isinstance(action, str):
        try:
            return ReviewAction(action)
        except ValueError:
            return ReviewAction.COMPLETE
    return ReviewAction.COMPLETE

async def interpret_request(state: AgentState) -> dict[str, Any]:
    if state.get("request"):
        return {}

    raw_prompt = state.get("raw_prompt")
    if not raw_prompt:
        raise ValueError("Agent state missing 'request' or 'raw_prompt'")

    reasoner = get_reasoning_agent()
    hints = state.get("request_hints") or {}
    interpretation = await reasoner.interpret_prompt(raw_prompt, hints=hints)

    request_id_hint = state.get("request_id_hint")
    request_obj = interpretation.request
    if request_id_hint:
        request_obj = request_obj.model_copy(update={"request_id": request_id_hint})
        interpretation.request = request_obj

    notes = list(state.get("working_notes") or [])
    if interpretation.rationale:
        notes.append(interpretation.rationale)

    interpretation_notes = list(state.get("interpretation_notes") or [])
    if interpretation.rationale:
        interpretation_notes.append(interpretation.rationale)

    event = AgentEvent(
        type="intake.interpretation",
        message="Interpreted natural language prompt",
        data={
            "used_llm": interpretation.used_llm,
            "raw_prompt_preview": raw_prompt[:200],
        },
    )

    updates: dict[str, Any] = {
        "status": WorkflowStatus.INTERPRETING,
        "request": request_obj,
        "working_notes": notes,
        "interpretation_notes": interpretation_notes,
        "events": _with_event(state, event),
    }

    if interpretation.raw_response:
        event.data["llm_response_preview"] = interpretation.raw_response[:200]

    return updates


async def route_request(state: AgentState) -> dict[str, Any]:
    request = _require_request(state)
    reasoner = get_reasoning_agent()

    # Gather prior notes and review feedback for intelligent replanning
    prior_notes = list(state.get("working_notes") or [])

    # If this is a retry, incorporate review feedback into routing decision
    retry_count = int(state.get("retry_count") or 0)
    if retry_count > 0:
        review_feedback = state.get("review_feedback")
        if review_feedback and review_feedback.review_notes:
            notes_obj = review_feedback.review_notes

            # Add context from previous attempt
            prior_notes.append(f"[Retry {retry_count}] Previous attempt completed at stage: {notes_obj.workflow_stage}")

            # Add successful steps to avoid repeating what worked
            if notes_obj.successful_steps:
                prior_notes.append(f"Successful steps: {', '.join(notes_obj.successful_steps[:3])}")

            # Add issue context for better decision making
            if notes_obj.issues_found:
                issue_categories = {issue.category.value for issue in notes_obj.issues_found}
                prior_notes.append(f"Issues encountered: {', '.join(issue_categories)}")

            # Add recommendations from review
            if notes_obj.recommendations:
                prior_notes.append(f"Recommendations: {'; '.join(notes_obj.recommendations[:2])}")

            # Add specific routing context
            if notes_obj.routing_context:
                if notes_obj.routing_context.get("failed_plugin"):
                    prior_notes.append(
                        f"Avoid plugin: {notes_obj.routing_context['failed_plugin']}"
                    )
                if notes_obj.routing_context.get("policy_blocked"):
                    prior_notes.append(
                        f"Policy constraint: {notes_obj.routing_context.get('policy_reason', 'unknown')}"
                    )

    decision = await reasoner.decide_workflow(request, prior_notes=prior_notes)
    workflow = decision.workflow or "generic-task"

    note = decision.rationale or f"Routed intent '{request.intent}' to workflow '{workflow}'"
    notes = prior_notes  # Keep accumulated notes
    notes.append(note)

    event = AgentEvent(
        type="router.decision",
        message=note,
        data={
            "request_id": request.request_id,
            "channel": request.channel,
            "decision_tags": decision.tags,
            "retry_count": retry_count,
        },
    )
    return {
        "status": WorkflowStatus.ROUTING,
        "selected_workflow": workflow,
        "working_notes": notes,
        "events": _with_event(state, event),
    }


async def policy_check(state: AgentState) -> dict[str, Any]:
    request = _require_request(state)
    feedback_agent = get_policy_feedback_agent()
    captured_directives = feedback_agent.capture(request)
    policy_engine = get_policy_engine()
    decision: PolicyDecision = policy_engine.evaluate(request)
    reasoner = get_reasoning_agent()
    notes = list(state.get("working_notes") or [])
    note = f"Policy decision: {decision.reason}"
    notes.append(note)
    if captured_directives:
        notes.append(f"Captured {len(captured_directives)} policy directive(s)")

    policy_analysis = await reasoner.assess_policy(request, decision)
    if policy_analysis:
        notes.append(f"Policy analysis: {policy_analysis}")

    event = AgentEvent(
        type="policy.review",
        message=note,
        data={
            "allowed": decision.allowed,
            "requires_human": decision.requires_human,
            "policy_version": decision.policy_version,
            "captured_directives": [directive.to_record() for directive in captured_directives]
            if captured_directives
            else [],
            "llm_analysis": policy_analysis,
        },
    )
    if not decision.allowed:
        raise PermissionError(decision.reason)

    return {
        "status": WorkflowStatus.POLICY_CHECK,
        "policy_decision": decision,
        "requires_human_approval": decision.requires_human or state.get("requires_human_approval", False),
        "working_notes": notes,
        "captured_policy_directives": [directive.to_record() for directive in captured_directives]
        if captured_directives
        else [],
        "events": _with_event(state, event),
    }


async def fetch_context(state: AgentState) -> dict[str, Any]:
    request = _require_request(state)
    memory_service = get_memory_service()
    snapshot = await memory_service.retrieve_context(request)
    validation = memory_service.validate_relevance(snapshot, request.intent)
    notes = list(state.get("working_notes") or [])
    notes.append(f"Context hydrated from {memory_service.provider} memory layer")

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


async def plan_actions(state: AgentState) -> dict[str, Any]:
    request = _require_request(state)
    reasoner = get_reasoning_agent()
    workflow = state.get("selected_workflow", "generic-task")
    context = state.get("retrieved_context")

    plan = await reasoner.build_plan(request, workflow=workflow, context=context)

    notes = list(state.get("working_notes") or [])
    notes.append(f"Planning agent proposed {len(plan)} step(s) for workflow '{workflow}'")

    event = AgentEvent(
        type="planner.plan_created",
        message="Created high-level plan",
        data={"steps": len(plan), "workflow": workflow},
    )
    return {
        "status": WorkflowStatus.PLANNING,
        "planned_actions": plan,
        "working_notes": notes,
        "events": _with_event(state, event),
    }


async def agent_reflection(state: AgentState) -> dict[str, Any]:
    request = _require_request(state)
    reasoner = get_reasoning_agent()
    workflow = state.get("selected_workflow", "generic-task")
    plan = state.get("planned_actions", [])
    context = state.get("retrieved_context") or {}
    validation = state.get("context_validation") or {}
    policy_decision = state.get("policy_decision")

    reflection = await reasoner.generate_reflection(
        request,
        workflow=workflow,
        plan=plan,
        context=context,
        validation=validation,
        policy_decision=policy_decision,
    )

    notes = list(state.get("working_notes") or [])
    notes.append("Reasoning agent produced reflection summary")

    event = AgentEvent(
        type="agent.reflect",
        message="Generated reasoning summary",
        data={"summary": reflection, "workflow": workflow},
    )

    return {
        "status": WorkflowStatus.REFLECTING,
        "analysis_summary": reflection,
        "working_notes": notes,
        "events": _with_event(state, event),
    }


async def select_plugin(state: AgentState) -> dict[str, Any]:
    request = _require_request(state)
    reasoner = get_reasoning_agent()
    workflow = state.get("selected_workflow", "generic-task")
    plan = state.get("planned_actions", [])
    metadata = request.metadata or {}

    decision = await reasoner.choose_plugin(request, workflow=workflow, plan=plan)

    notes = list(state.get("working_notes") or [])
    notes.append(decision.rationale)

    event = AgentEvent(
        type="plugin.selected",
        message=f"Candidate plugin '{decision.plugin_name}' chosen",
        data={
            "preferred": metadata.get("plugin"),
            "channel": request.channel,
            "confidence": decision.confidence,
            "rationale": decision.rationale,
        },
    )
    return {
        "selected_plugin": decision.plugin_name,
        "working_notes": notes,
        "events": _with_event(state, event),
    }


async def render_payload(state: AgentState) -> dict[str, Any]:
    request = _require_request(state)
    reasoner = get_reasoning_agent()
    payload = request.payload or {}
    template = payload.get("template") or "[demo] {intent}"
    variables = {"intent": request.intent, **payload.get("variables", {})}
    try:
        rendered = template.format(**variables)
    except KeyError:
        rendered = f"{template} | vars={variables}"

    plan = state.get("planned_actions", [])
    context = state.get("retrieved_context") or {}
    rendered_message = await reasoner.generate_payload(
        request,
        plan=plan,
        context=context,
        fallback=rendered,
    )

    event = AgentEvent(
        type="message.rendered",
        message="Rendered payload for plugin dispatch",
        data={"char_count": len(rendered_message)},
    )
    return {
        "rendered_message": rendered_message,
        "events": _with_event(state, event),
    }


async def execute_plugin(state: AgentState) -> dict[str, Any]:
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


async def review_outcome(state: AgentState) -> dict[str, Any]:
    sentinel = get_agent_sentinel()
    feedback: ReviewFeedback = await sentinel.review(state)
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


def run_review_agent(state: AgentState) -> dict[str, Any]:
    agent = get_review_agent()
    action, message = agent.evaluate(state)
    notes = list(state.get("working_notes") or [])
    if message:
        notes.append(message)

    retry_count = int(state.get("retry_count") or 0)
    updates: dict[str, Any] = {
        "review_agent_message": message,
        "review_action": action,
        "working_notes": notes,
    }

    event = AgentEvent(
        type="review.agent",
        message=message or "Review agent processed workflow",
        data={
            "action": action.value,
            "retry_count": retry_count,
        },
    )

    if action == ReviewAction.RETRY:
        retry_count += 1
        updates["retry_count"] = retry_count
        updates["requires_human_approval"] = False
        updates["status"] = WorkflowStatus.ROUTING
        event.data["retry_count"] = retry_count
        updates.update(
            {
                "selected_plugin": None,
                "rendered_message": None,
                "plugin_result": None,
                "review_feedback": None,
                "policy_decision": None,
                "analysis_summary": None,
                "planned_actions": [],
                "retrieved_context": {},
                "context_validation": {},
            }
        )
    else:
        updates["retry_count"] = retry_count
        updates["status"] = WorkflowStatus.REVIEWING

    updates["events"] = _with_event(state, event)
    return updates


async def update_memory(state: AgentState) -> dict[str, Any]:
    request = _require_request(state)
    memory_service = get_memory_service()
    plugin_result: PluginDispatchResult | None = state.get("plugin_result")
    reflection: str = state.get("analysis_summary", "")
    updates: list[MemoryUpdate] = memory_service.prepare_updates(request, plugin_result, reflection)

    await memory_service.commit_updates(request, updates)

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


def finalize(state: AgentState) -> dict[str, Any]:
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


def build_langgraph(checkpointer: InMemorySaver | None = None) -> Any:
    builder = StateGraph(AgentState)
    builder.add_node("interpret_request", interpret_request)
    builder.add_node("route_request", route_request)
    builder.add_node("policy_check", policy_check)
    builder.add_node("fetch_context", fetch_context)
    builder.add_node("plan_actions", plan_actions)
    builder.add_node("agent_reflection", agent_reflection)
    builder.add_node("select_plugin", select_plugin)
    builder.add_node("render_payload", render_payload)
    builder.add_node("execute_plugin", execute_plugin)
    builder.add_node("review_outcome", review_outcome)
    builder.add_node("review_agent", run_review_agent)
    builder.add_node("update_memory", update_memory)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "interpret_request")
    builder.add_edge("interpret_request", "route_request")
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
    builder.add_edge("review_outcome", "review_agent")
    builder.add_conditional_edges(
        "review_agent",
        _review_route,
        {
            ReviewAction.RETRY: "route_request",
            ReviewAction.COMPLETE: "update_memory",
        },
    )
    builder.add_edge("update_memory", "finalize")
    builder.add_edge("finalize", END)

    checkpointer = checkpointer or InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
