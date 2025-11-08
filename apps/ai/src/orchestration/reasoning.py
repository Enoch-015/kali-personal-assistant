from __future__ import annotations

import inspect
import logging
import os
import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

from src.orchestration.models import OrchestrationRequest, PolicyDecision, PluginDispatchResult
from src.orchestration.plugins.base import registry as plugin_registry
from pydantic import ValidationError

PROMPT_DEFINITIONS = (
    "Definitions:\n"
    "- Intent: short description of the user's goal that the workflow should satisfy.\n"
    "- Channel: delivery medium or plugin category that will execute the task (e.g. email, whatsapp).\n"
    "- Audience: recipients or target segment that should receive the outcome.\n"
    "- Payload: structured content or template data that is sent to the plugin.\n"
    "- Metadata: supporting key/value context such as user_id or priority.\n"
)


@dataclass
class WorkflowDecision:
    """Represents the workflow routing decision produced by the reasoning agent."""

    workflow: str
    rationale: str
    tags: List[str] = field(default_factory=list)


@dataclass
class PluginDecision:
    """Represents the plugin dispatch strategy chosen by the reasoning agent."""

    plugin_name: str
    rationale: str
    confidence: float = 0.5


@dataclass
class RequestInterpretation:
    """Represents the interpreted orchestration request extracted from natural language."""

    request: OrchestrationRequest
    rationale: str
    used_llm: bool = False
    raw_response: Optional[str] = None


@dataclass
class ReviewAssessment:
    """Represents the governance assessment produced by the reasoning agent."""

    summary: str
    requires_human: bool
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class OrchestrationReasoner:
    """Lightweight reasoning helper that optionally delegates to an LLM.

    The class provides deterministic fallbacks to keep test execution stable while
    allowing projects to inject an async-compatible chat model (anything that
    implements ``ainvoke`` or is awaitable/callable) for richer reasoning at runtime.
    """

    def __init__(self, llm: Optional[Any] = None) -> None:
        self._llm = llm

    async def interpret_prompt(
        self,
        prompt: str,
        *,
        hints: Optional[Dict[str, Any]] = None,
    ) -> RequestInterpretation:
        """Interpret a natural language prompt into an orchestration request."""

        hints = hints or {}
        normalized = (prompt or "").strip()
        fallback_intent = normalized or "general_assistance"

        base_data: Dict[str, Any] = {
            "intent": fallback_intent,
            "channel": str(hints.get("channel") or "demo").strip() or "demo",
            "payload": hints.get("payload") or {},
            "metadata": dict(hints.get("metadata") or {}),
        }

        audience_hint = hints.get("audience")
        if audience_hint:
            base_data["audience"] = audience_hint

        try:
            base_request = OrchestrationRequest.model_validate(base_data)
        except ValidationError:
            base_data.pop("audience", None)
            base_request = OrchestrationRequest.model_validate(base_data)

        hints_json = json.dumps(hints, ensure_ascii=False) if hints else "{}"
        llm_prompt = (
            "You are an orchestration intake specialist responsible for translating natural language into"
            " the structured OrchestrationRequest format.\n"
            f"{PROMPT_DEFINITIONS}"
            "Return a JSON object with keys: intent (string), channel (string), audience (object with optional\n"
            "  \"recipients\" array), payload (object), metadata (object), and rationale (string summarizing your interpretation).\n"
            "Ensure recipients are valid addresses or identifiers when applicable and preserve helpful details from the prompt.\n"
            f"Raw prompt: {normalized or prompt}\n"
            f"Hints (optional structured guidance): {hints_json}"
        )

        rationale = "Default interpretation applied"
        used_llm = False
        raw_response: Optional[str] = None
        llm_response = await self._call_llm_if_configured(llm_prompt)
        if llm_response:
            raw_response = llm_response
            try:
                parsed = json.loads(llm_response)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                candidate_data: Dict[str, Any] = {
                    "intent": str(parsed.get("intent") or base_request.intent).strip() or base_request.intent,
                    "channel": str(parsed.get("channel") or base_request.channel).strip() or base_request.channel,
                    "payload": parsed.get("payload") or base_request.payload,
                    "metadata": {
                        **base_request.metadata,
                        **((parsed.get("metadata") or {}) if isinstance(parsed.get("metadata"), dict) else {}),
                    },
                }
                audience_candidate = parsed.get("audience")
                if audience_candidate:
                    candidate_data["audience"] = audience_candidate
                try:
                    interpreted_request = OrchestrationRequest.model_validate(candidate_data)
                except ValidationError:
                    candidate_data.pop("audience", None)
                    interpreted_request = OrchestrationRequest.model_validate(candidate_data)
                base_request = interpreted_request
                rationale = str(parsed.get("rationale") or "LLM interpretation applied")
                used_llm = True
            else:
                rationale = llm_response.strip() or rationale
                used_llm = True

        return RequestInterpretation(
            request=base_request,
            rationale=rationale,
            used_llm=used_llm,
            raw_response=raw_response,
        )

    async def decide_workflow(
        self,
        request: OrchestrationRequest,
        *,
        prior_notes: Optional[Sequence[str]] = None,
    ) -> WorkflowDecision:
        metadata = request.metadata or {}
        explicit = metadata.get("workflow")
        tags: List[str] = []

        if isinstance(explicit, str) and explicit.strip():
            workflow = explicit.strip()
            rationale = "Caller pinned workflow via metadata"
            tags.append("source:metadata")
        elif request.audience and request.audience.recipients:
            workflow = "broadcast"
            rationale = "Audience provided; defaulting to broadcast workflow"
            tags.append("source:audience")
        else:
            workflow = "generic-task"
            rationale = "No audience or explicit workflow; using generic-task baseline"
            tags.append("source:heuristic")

        llm_reason = await self._call_llm_if_configured(
            self._format_prompt(
                "workflow",
                request,
                context_summary=self._summarize_notes(prior_notes),
                default_reason=rationale,
            )
        )
        if llm_reason:
            rationale = llm_reason

        return WorkflowDecision(workflow=workflow, rationale=rationale, tags=tags)

    async def build_plan(
        self,
        request: OrchestrationRequest,
        *,
        workflow: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []
        step_counter = 1

        steps.append(
            {
                "step": step_counter,
                "action": "analyse_intent",
                "details": request.intent,
                "rationale": "Understand the caller's goal",
                "source": "reasoner",
            }
        )
        step_counter += 1

        snippet_count = len((context or {}).get("memory_snippets") or [])
        if snippet_count:
            steps.append(
                {
                    "step": step_counter,
                    "action": "inspect_context",
                    "details": f"Review {snippet_count} relevant memory snippet(s)",
                    "rationale": "Ground the plan with retrieved memory",
                    "source": "reasoner",
                }
            )
            step_counter += 1

        steps.append(
            {
                "step": step_counter,
                "action": "prepare_tool_invocation",
                "details": workflow,
                "rationale": "Select delivery channel or plugin",
                "source": "reasoner",
            }
        )

        llm_plan = await self._call_llm_if_configured(
            self._format_prompt(
                "planning",
                request,
                context_summary=self._summarize_context(context),
                default_reason=str(steps),
            )
        )
        if llm_plan:
            steps = self._merge_llm_plan(steps, llm_plan)

        return steps

    async def generate_reflection(
        self,
        request: OrchestrationRequest,
        *,
        workflow: str,
        plan: Sequence[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        validation: Optional[Dict[str, Any]] = None,
        policy_decision: Optional[PolicyDecision] = None,
        plugin_name: Optional[str] = None,
    ) -> str:
        snippet_count = len((context or {}).get("memory_snippets") or [])
        relation_count = len((context or {}).get("graph_relations") or [])
        validation_summary = (validation or {}).get("summary", "")

        parts = [
            f"Intent: {request.intent}",
            f"Workflow: {workflow}",
            f"Plan steps: {len(list(plan))}",
            f"Memory snippets: {snippet_count}",
            f"Graph relations: {relation_count}",
        ]
        if validation_summary:
            parts.append(f"Validation: {validation_summary}")
        if policy_decision is not None:
            parts.append(f"Policy: {policy_decision.reason}")
        if plugin_name:
            parts.append(f"Plugin: {plugin_name}")

        fallback = " | ".join(part for part in parts if part)

        llm_summary = await self._call_llm_if_configured(
            self._format_prompt(
                "reflection",
                request,
                context_summary=self._summarize_context(context),
                plan_summary=self._summarize_plan(plan),
                default_reason=fallback,
            )
        )
        return llm_summary or fallback

    async def assess_policy(
        self,
        request: OrchestrationRequest,
        decision: PolicyDecision,
    ) -> Optional[str]:
        """Provide an LLM-backed assessment of the policy decision."""

        summary = (
            f"Policy decision: allowed={decision.allowed}, requires_human={decision.requires_human},"
            f" reason={decision.reason or 'n/a'}"
        )
        prompt = (
            "You are the governance analyst reviewing a policy decision for an orchestration request.\n"
            f"{PROMPT_DEFINITIONS}"
            f"Intent: {request.intent}\n"
            f"Channel: {request.channel}\n"
            f"Policy allowed: {decision.allowed}\n"
            f"Requires human: {decision.requires_human}\n"
            f"Policy rationale: {decision.reason}\n"
            f"Policy tags: {', '.join(decision.tags) if decision.tags else 'none'}\n"
            "Respond with a concise analysis highlighting potential risks or actions."
        )
        analysis = await self._call_llm_if_configured(prompt)
        return analysis or summary

    async def choose_plugin(
        self,
        request: OrchestrationRequest,
        *,
        workflow: str,
        plan: Sequence[Dict[str, Any]],
    ) -> PluginDecision:
        metadata = request.metadata or {}
        preferred = metadata.get("plugin")
        if isinstance(preferred, str) and preferred.strip():
            candidate = preferred.strip()
            rationale = "Caller requested plugin explicitly"
            confidence = 0.9
        else:
            candidate = (request.channel or "").strip() or "demo-messaging"
            if workflow == "generic-task" and candidate == "":
                candidate = "demo-messaging"
            if workflow == "generic-task" and candidate != "demo-messaging":
                rationale = "Generic workflow defers to demo plugin"
                candidate = "demo-messaging"
                confidence = 0.6
            else:
                rationale = f"Selected plugin based on channel '{request.channel or 'demo'}'"
                confidence = 0.7

        available_plugins = ", ".join(sorted(plugin_registry.names())) or "demo-messaging"
        plugin_context = (
            "Available plugins you may choose from: "
            f"{available_plugins}. Only select one of these registered plugin names."
        )

        llm_choice = await self._call_llm_if_configured(
            self._format_prompt(
                "plugin",
                request,
                plan_summary=self._summarize_plan(plan),
                default_reason=f"{candidate}::{rationale}",
                extra_context=plugin_context,
            )
        )

        if llm_choice:
            parsed = self._parse_plugin_response(llm_choice)
            if parsed is not None:
                proposed_name, explanation = parsed
                if plugin_registry.get(proposed_name):
                    candidate = proposed_name
                    rationale = explanation
                    confidence = 0.75
                else:
                    _LOGGER.debug(
                        "Ignoring reasoning plugin proposal '%s' because no plugin is registered under that name",
                        proposed_name,
                    )

        return PluginDecision(plugin_name=candidate, rationale=rationale, confidence=confidence)

    async def generate_payload(
        self,
        request: OrchestrationRequest,
        *,
        plan: Sequence[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        fallback: str,
    ) -> str:
        """Draft a payload message using the LLM when available."""

        prompt = (
            "You are a communications specialist tasked with drafting the final message for an orchestration workflow.\n"
            f"{PROMPT_DEFINITIONS}"
            f"Intent (user goal): {request.intent}\n"
            f"Channel (delivery medium): {request.channel}\n"
            f"Plan summary: {self._summarize_plan(plan) or 'none'}\n"
            f"Provided payload template: {json.dumps(request.payload or {}, ensure_ascii=False)}\n"
            f"Context summary: {self._summarize_context(context)}\n"
            "Compose the exact message to send. Keep it concise, actionable, and aligned with the intent."
        )
        llm_message = await self._call_llm_if_configured(prompt)
        if llm_message:
            return llm_message
        return fallback

    async def assess_review(
        self,
        request: OrchestrationRequest,
        *,
        workflow: str,
        status: str,
        planned_actions: Sequence[Dict[str, Any]],
        analysis_summary: Optional[str],
        plugin_result: Optional[PluginDispatchResult],
        policy_decision: Optional[PolicyDecision],
        context_validation: Optional[Dict[str, Any]],
        issues: Sequence[str],
        recommendations: Sequence[str],
    ) -> ReviewAssessment:
        plan_summary = self._summarize_plan(planned_actions)
        validation_summary = (context_validation or {}).get("summary") or "n/a"

        plugin_snapshot = "None"
        if plugin_result:
            failures = len(plugin_result.failed)
            plugin_snapshot = (
                f"{plugin_result.plugin_name} dispatched={plugin_result.dispatched_count} failed={failures}"
            )

        policy_snapshot = "None"
        if policy_decision is not None:
            policy_snapshot = (
                f"allowed={policy_decision.allowed} requires_human={policy_decision.requires_human}"
                f" reason={policy_decision.reason}"
            )

        fallback_summary = (
            f"Workflow '{workflow}' finished at stage '{status}'. Plan steps: "
            f"{plan_summary or 'n/a'}. Plugin: {plugin_snapshot}."
        )

        issue_text = "; ".join(str(item) for item in issues if item) or "None"
        recommendation_text = "; ".join(str(item) for item in recommendations if item) or "None"

        prompt = (
            "You are the governance sentinel overseeing an AI orchestration workflow.\n"
            f"{PROMPT_DEFINITIONS}"
            f"Intent: {request.intent}\n"
            f"Channel: {request.channel}\n"
            f"Workflow: {workflow}\n"
            f"Final stage: {status}\n"
            f"Plan summary: {plan_summary or 'n/a'}\n"
            f"Analysis summary: {analysis_summary or 'n/a'}\n"
            f"Plugin result: {plugin_snapshot}\n"
            f"Policy decision: {policy_snapshot}\n"
            f"Context validation: {validation_summary}\n"
            f"Existing issues: {issue_text}\n"
            f"Existing recommendations: {recommendation_text}\n"
            "Respond with a JSON object containing keys 'summary' (string), 'requires_human' (boolean),\n"
            "'issues' (array of concise issue descriptions), and 'recommendations' (array of actionable suggestions)."
        )

        llm_response = await self._call_llm_if_configured(prompt)
        if not llm_response:
            return ReviewAssessment(summary=fallback_summary, requires_human=False)

        summary = fallback_summary
        requires_human = False
        issues_out: List[str] = []
        recs_out: List[str] = []

        try:
            parsed = json.loads(llm_response)
            if isinstance(parsed, dict):
                summary = str(parsed.get("summary") or fallback_summary)
                requires_human = bool(parsed.get("requires_human", False))
                raw_issues = parsed.get("issues", [])
                if isinstance(raw_issues, list):
                    issues_out = [str(item).strip() for item in raw_issues if str(item).strip()]
                raw_recs = parsed.get("recommendations", [])
                if isinstance(raw_recs, list):
                    recs_out = [str(item).strip() for item in raw_recs if str(item).strip()]
            else:
                summary = str(parsed)
        except json.JSONDecodeError:
            cleaned = llm_response.strip()
            summary = cleaned or fallback_summary
            requires_human = "requires" in cleaned.lower() or "human" in cleaned.lower()

        return ReviewAssessment(
            summary=summary,
            requires_human=requires_human,
            issues=issues_out,
            recommendations=recs_out,
        )


    async def _call_llm_if_configured(self, prompt: Optional[str]) -> Optional[str]:
        if not prompt or self._llm is None:
            return None
        model = self._llm
        try:
            if hasattr(model, "ainvoke"):
                response = await model.ainvoke(prompt)
            elif hasattr(model, "invoke"):
                response = model.invoke(prompt)  # type: ignore[assignment]
            elif callable(model):
                response = model(prompt)
            else:
                return None
            if inspect.isawaitable(response):
                response = await response
        except Exception:  # pragma: no cover - model errors should not break orchestration
            return None

        content = getattr(response, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(response, str):
            return response.strip()
        return None

    def _merge_llm_plan(self, base: List[Dict[str, Any]], llm_response: str) -> List[Dict[str, Any]]:
        lines = [line.strip() for line in llm_response.splitlines() if line.strip()]
        merged: List[Dict[str, Any]] = []
        for index, line in enumerate(lines, start=1):
            merged.append(
                {
                    "step": index,
                    "action": line.split(" ")[0].lower(),
                    "details": line,
                    "rationale": "LLM provided",
                    "source": "reasoner-llm",
                }
            )
        return merged or base

    def _parse_plugin_response(self, response: str) -> Optional[tuple[str, str]]:
        tokens = response.split("::", maxsplit=1)
        if len(tokens) == 2:
            name, explanation = tokens
            name = name.strip()
            if name:
                return name, explanation.strip() or "LLM provided plugin rationale"
        response = response.strip()
        if response and len(response.split()) == 1:
            return response, "LLM selected plugin"
        return None

    def _summarize_context(self, context: Optional[Dict[str, Any]]) -> str:
        if not context:
            return ""
        snippets = context.get("memory_snippets") or []
        relations = context.get("graph_relations") or []
        return f"snippets={len(snippets)}, relations={len(relations)}"

    def _summarize_plan(self, plan: Sequence[Dict[str, Any]]) -> str:
        if not plan:
            return ""
        actions = [str(item.get("action", "")) for item in plan if isinstance(item, dict)]
        return ", ".join(filter(None, actions))

    def _summarize_notes(self, notes: Optional[Sequence[str]]) -> str:
        if not notes:
            return ""
        return " | ".join(notes)

    def _format_prompt(
        self,
        topic: str,
        request: OrchestrationRequest,
        *,
        context_summary: str = "",
        plan_summary: str = "",
        default_reason: str,
        extra_context: str = "",
    ) -> str:
        format_hint = "Respond with a concise rationale."
        if topic == "plugin":
            format_hint = (
                "Respond with '<plugin_name>::<short rationale>' using the name of a registered plugin."
            )
        elif topic == "workflow":
            format_hint = "Respond with '<workflow>::<short rationale>'"
        elif topic == "planning":
            format_hint = "List plan steps succinctly."
        elif topic == "reflection":
            format_hint = "Provide a short summary highlighting key observations."
        elif topic == "review":
            format_hint = (
                "Respond with JSON: {\"summary\": str, \"requires_human\": bool,"
                " \"issues\": [str], \"recommendations\": [str]}"
            )
        elif topic == "interpretation":
            format_hint = (
                "Respond with JSON {\"intent\": str, \"channel\": str, \"audience\": object,"
                " \"payload\": object, \"metadata\": object, \"rationale\": str}"
            )
        elif topic == "payload":
            format_hint = "Respond with the final message text."
        elif topic == "policy":
            format_hint = "Provide a risk-focused analysis and recommendations."

        prompt = (
            f"Topic: {topic}\n"
            f"Intent: {request.intent}\n"
            f"Channel: {request.channel}\n"
            f"Context: {context_summary or 'none'}\n"
            f"Plan: {plan_summary or 'n/a'}\n"
            f"{format_hint}\n"
            f"{PROMPT_DEFINITIONS}"
            f"Default: {default_reason}"
        )

        if extra_context:
            prompt = f"{prompt}\nAdditional context: {extra_context}"

        return prompt


_REASONING_LLM: Optional[Any] = None
_LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from langchain_openai import AzureChatOpenAI, ChatOpenAI
except ImportError:  # pragma: no cover - optional dependency may be missing
    ChatOpenAI = None  # type: ignore[assignment]
    AzureChatOpenAI = None  # type: ignore[assignment]


def configure_reasoning_llm(llm: Optional[Any]) -> None:
    """Replace the global reasoning LLM and reset the cached helper."""

    global _REASONING_LLM
    _REASONING_LLM = llm
    get_reasoning_agent.cache_clear()  # type: ignore[attr-defined]


@lru_cache(maxsize=1)
def get_reasoning_agent() -> OrchestrationReasoner:
    return OrchestrationReasoner(llm=_REASONING_LLM)


def configure_reasoning_from_settings(settings: Any) -> bool:
    """Configure the reasoning LLM using project settings.

    Returns True when a compatible model is successfully configured.
    """

    graphiti = getattr(settings, "graphiti", None)
    provider = getattr(graphiti, "llm_provider", "openai") or "openai"
    provider = str(provider).lower()
    llm: Any = None

    if provider == "openai":
        if ChatOpenAI is None:
            _LOGGER.info("langchain-openai is not installed; skipping reasoning LLM wiring")
            return False
        api_key = (
            getattr(graphiti, "openai_api_key", None)
            or os.getenv("OPENAI_API_KEY")
        )
        model = getattr(graphiti, "openai_model", None) or "gpt-4o"
        if not api_key:
            _LOGGER.debug("No OpenAI API key detected for reasoning agent")
            return False
        llm = ChatOpenAI(  # type: ignore[call-arg]
            model=model,
            api_key=api_key,
            temperature=0.0,
            max_retries=2,
        )
    elif provider == "azure":
        if AzureChatOpenAI is None:
            _LOGGER.info("langchain-openai Azure client unavailable; skipping reasoning LLM wiring")
            return False
        api_key = (
            getattr(graphiti, "openai_api_key", None)
            or os.getenv("AZURE_OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        endpoint = getattr(graphiti, "azure_openai_endpoint", None)
        deployment = getattr(graphiti, "azure_openai_deployment_name", None)
        api_version = getattr(graphiti, "azure_openai_api_version", None)
        model = getattr(graphiti, "openai_model", None) or "gpt-4o"
        if not all([api_key, endpoint, deployment, api_version]):
            _LOGGER.debug("Incomplete Azure OpenAI configuration for reasoning agent")
            return False
        llm = AzureChatOpenAI(  # type: ignore[call-arg]
            api_key=api_key,
            azure_endpoint=endpoint,
            azure_deployment=deployment,
            api_version=api_version,
            model=model,
            temperature=0.0,
            max_retries=2,
        )
    else:
        _LOGGER.debug("Reasoning LLM provider '%s' not supported", provider)
        return False

    configure_reasoning_llm(llm)
    _LOGGER.info("Configured reasoning LLM using provider '%s'", provider)
    return True
