"""Invoke the /ai/graph/invoke endpoint with a natural language prompt."""

import argparse
import asyncio
import json
from typing import Any

import httpx


def _parse_kv_pairs(pairs: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for item in pairs:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"Expected key=value format, got '{item}'")
        key, value = item.split("=", 1)
        data[key] = value
    return data


async def invoke(prompt: str, mode: str, hints: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": prompt}
    if hints:
        payload["hints"] = hints

    url = f"http://localhost:8000/ai/graph/invoke?mode={mode}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Invoke the AI graph endpoint with a natural language request.")
    parser.add_argument("prompt", help="Natural language instruction to send to the AI graph")
    parser.add_argument("--mode", choices=["sync", "async"], default="sync", help="Execution mode for the request")
    parser.add_argument("--channel", help="Preferred delivery channel (email, whatsapp, etc.)")
    parser.add_argument(
        "--recipient",
        action="append",
        default=[],
        help="Recipient identifier. Repeat to provide multiple recipients.",
    )
    parser.add_argument("--segment-id", help="Audience segment identifier")
    parser.add_argument("--payload-template", help="Template string for the payload")
    parser.add_argument(
        "--payload-var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Payload template variable. Repeat for multiple values.",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Metadata entry to attach to the request. Repeat for multiple values.",
    )
    return parser


def build_hints(args: argparse.Namespace) -> dict[str, Any]:
    hints: dict[str, Any] = {}
    if args.channel:
        hints["channel"] = args.channel

    audience: dict[str, Any] = {}
    if args.recipient:
        audience["recipients"] = args.recipient
    if args.segment_id:
        audience["segment_id"] = args.segment_id
    if audience:
        hints["audience"] = audience

    payload: dict[str, Any] = {}
    if args.payload_template:
        payload["template"] = args.payload_template
    if args.payload_var:
        payload["variables"] = _parse_kv_pairs(args.payload_var)
    if payload:
        hints["payload"] = payload

    if args.metadata:
        hints["metadata"] = _parse_kv_pairs(args.metadata)

    return hints


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    hints = build_hints(args)

    try:
        result = asyncio.run(invoke(args.prompt, args.mode, hints))
    except httpx.HTTPStatusError as exc:
        print(f"Request failed with status {exc.response.status_code} - {exc.response.text}")
        raise SystemExit(1) from exc
    except Exception as exc:  # pragma: no cover - network/connection errors
        print(f"Request failed: {exc}")
        raise SystemExit(1) from exc

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
