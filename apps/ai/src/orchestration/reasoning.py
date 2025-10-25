from __future__ import annotations

import inspect
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

from src.orchestration.models import OrchestrationRequest, PolicyDecision
from src.orchestration.plugins.base import registry as plugin_registry


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


class OrchestrationReasoner:
    """Lightweight reasoning helper that optionally delegates to an LLM.

    The class provides deterministic fallbacks to keep test execution stable while
    allowing projects to inject an async-compatible chat model (anything that
    implements ``ainvoke`` or is awaitable/callable) for richer reasoning at runtime.
    """

    def __init__(self, llm: Optional[Any] = None) -> None:
        self._llm = llm

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

        llm_choice = await self._call_llm_if_configured(
            self._format_prompt(
                "plugin",
                request,
                plan_summary=self._summarize_plan(plan),
                default_reason=f"{candidate}::{rationale}",
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

        return (
            f"Topic: {topic}\n"
            f"Intent: {request.intent}\n"
            f"Channel: {request.channel}\n"
            f"Context: {context_summary or 'none'}\n"
            f"Plan: {plan_summary or 'n/a'}\n"
            f"{format_hint}\n"
            f"Default: {default_reason}"
        )


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
