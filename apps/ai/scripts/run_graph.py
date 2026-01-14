#!/usr/bin/env python3
"""Run the LangGraph orchestration manually with ad-hoc inputs."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

AI_ROOT = Path(__file__).resolve().parents[1]
APPS_ROOT = AI_ROOT.parent  # apps/ folder containing both ai/ and config/

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))
if str(APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(APPS_ROOT))

from config.settings import get_settings
from src.orchestration.graph import build_langgraph
from src.orchestration.models import Audience, OrchestrationRequest
from src.orchestration.plugins.demo import register_demo_plugin
from src.orchestration.reasoning import configure_reasoning_from_settings


def _parse_json(value: Optional[str], *, label: str) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:  # pragma: no cover - user input guard
        raise SystemExit(f"Failed to parse {label} JSON: {exc}")
    if not isinstance(parsed, dict):
        raise SystemExit(f"{label} JSON must decode to an object")
    return parsed


def _dump_event_types(events: Iterable[Any]) -> str:
    types = []
    for event in events:
        type_name = getattr(event, "type", None)
        if type_name is None and isinstance(event, dict):
            type_name = event.get("type")
        types.append(str(type_name or "unknown"))
    return ", ".join(types) or "<none>"


def _maybe_dump(value: Any) -> Any:
    return value.model_dump() if hasattr(value, "model_dump") else value


async def _run_graph(args: argparse.Namespace, settings: Any) -> None:
    register_demo_plugin()
    configure_reasoning_from_settings(settings)

    payload = {"template": args.template, "variables": {"intent": args.intent}}
    payload.update(_parse_json(args.payload, label="payload"))
    metadata = _parse_json(args.metadata, label="metadata")

    audience = Audience(recipients=args.audience) if args.audience else None

    request = OrchestrationRequest(
        intent=args.intent,
        channel=args.channel,
        audience=audience,
        payload=payload,
        metadata=metadata,
    )

    graph = build_langgraph()
    config = {"configurable": {"thread_id": args.thread_id or request.request_id}}
    result = await graph.ainvoke({"request": request}, config=config)

    print("Status:", result.get("status"))
    print("Selected workflow:", result.get("selected_workflow"))
    print("Selected plugin:", result.get("selected_plugin"))
    plugin_result = result.get("plugin_result")
    if plugin_result:
        print("Plugin result:", json.dumps(_maybe_dump(plugin_result), indent=2))

    policy_decision = result.get("policy_decision")
    if policy_decision:
        print("Policy decision:", json.dumps(_maybe_dump(policy_decision), indent=2))

    review_feedback = result.get("review_feedback")
    if review_feedback:
        print("Review feedback:", json.dumps(_maybe_dump(review_feedback), indent=2))

    analysis = result.get("analysis_summary")
    if analysis:
        print("Analysis summary:", analysis)

    notes = result.get("working_notes") or []
    if notes:
        print("Working notes:")
        for note in notes:
            print(" •", note)

    events = result.get("events") or []
    if args.show_events and events:
        print("Events:")
        for event in events:
            payload = _maybe_dump(event)
            print(json.dumps(payload, indent=2))
    else:
        print("Events registered:", _dump_event_types(events))

    snapshots = result.get("retrieved_context")
    if args.show_context and snapshots:
        print("Retrieved context:", json.dumps(snapshots, indent=2))

    if args.show_updates and result.get("memory_updates"):
        updates = [_maybe_dump(update) for update in result["memory_updates"]]
        print("Memory updates:", json.dumps(updates, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute the agent LangGraph once with custom inputs")
    parser.add_argument("--intent", default="send_status_update", help="Intent passed to the orchestration graph")
    parser.add_argument("--channel", default="email", help="Primary delivery channel / plugin hint")
    parser.add_argument(
        "--audience",
        nargs="*",
        help="Recipients for the audience model; omit to run a generic-task workflow",
    )
    parser.add_argument(
        "--template",
        default="Hello {intent}",
        help="String template used to render the outbound payload",
    )
    parser.add_argument(
        "--payload",
        help="Additional payload JSON merged into the default template payload",
    )
    parser.add_argument(
        "--metadata",
        help="Metadata JSON passed to the orchestration request",
    )
    parser.add_argument(
        "--thread-id",
        help="Optional LangGraph thread identifier; defaults to the generated request id",
    )
    parser.add_argument(
        "--show-events",
        action="store_true",
        help="Print the full event payloads instead of just the event types",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Pretty-print the retrieved memory snapshot returned by the memory service",
    )
    parser.add_argument(
        "--show-updates",
        action="store_true",
        help="Pretty-print the memory updates generated at the end of the run",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = get_settings("ai")  # Uses apps/config/.env + apps/ai/.env
    try:
        asyncio.run(_run_graph(args, settings))
    except KeyboardInterrupt:  # pragma: no cover - runtime convenience
        parser.exit(status=130, message="\nInterrupted\n")


if __name__ == "__main__":
    main(sys.argv[1:])
