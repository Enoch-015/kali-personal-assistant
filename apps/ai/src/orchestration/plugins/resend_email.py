from __future__ import annotations

import asyncio
import html
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional

import resend

from src.config.settings import get_settings
from src.orchestration.models import OrchestrationRequest, PluginDispatchResult
from src.orchestration.plugins.base import BasePlugin, registry

logger = logging.getLogger(__name__)


def _flatten_recipients(values: Iterable[str | None]) -> List[str]:
    recipients: List[str] = []
    for value in values:
        if not value:
            continue
        parts = [part.strip() for part in str(value).split(",") if part and part.strip()]
        recipients.extend(parts)
    return recipients


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
    return bool(value)


def _default_html_from_text(rendered: str) -> str:
    stripped = rendered.strip()
    if not stripped:
        return "<p></p>"

    paragraphs = [segment.strip() for segment in stripped.split("\n\n") if segment.strip()]
    if not paragraphs:
        paragraphs = [stripped]

    html_parts: List[str] = []
    for para in paragraphs:
        lines = [html.escape(line.strip()) for line in para.splitlines() if line.strip()]
        if not lines:
            continue
        html_para = "<br>".join(lines)
        html_parts.append(f"<p>{html_para}</p>")

    return "".join(html_parts) if html_parts else "<p></p>"


_SUBJECT_PATTERN = re.compile(r"^\s*subject\s*:\s*(?P<subject>.+)$", re.IGNORECASE)


def _extract_subject_line(message: str) -> tuple[Optional[str], str]:
    if not isinstance(message, str):
        return None, ""

    lines = message.splitlines()
    first_non_empty_idx = None
    for idx, line in enumerate(lines):
        if line.strip():
            first_non_empty_idx = idx
            break

    if first_non_empty_idx is None:
        return None, message

    first_line = lines[first_non_empty_idx]
    match = _SUBJECT_PATTERN.match(first_line)
    if not match:
        return None, message

    subject_value = match.group("subject").strip()
    body_lines = lines[:first_non_empty_idx] + lines[first_non_empty_idx + 1 :]
    body_text = "\n".join(body_lines)
    return (subject_value or None), body_text


class ResendEmailPlugin(BasePlugin):
    """Dispatches email notifications through the Resend API."""

    name = "resend-email"
    description = "Dispatch email notifications using Resend with structured payload support."

    async def dispatch(
        self,
        request: OrchestrationRequest,
        message_body: str,
        *,
        context: Dict[str, Any] | None = None,
    ) -> PluginDispatchResult:
        context = context or {}
        settings = get_settings()
        resend_settings = settings.resend
        runtime = self._resolve_runtime_config(resend_settings)

        subject_hint, normalized_body = _extract_subject_line(message_body)
        recipients = self._determine_recipients(request, context, runtime["default_recipient"])
        if not recipients:
            raise ValueError("ResendEmailPlugin requires at least one recipient")

        subject = self._resolve_subject(request, context, subject_hint=subject_hint)
        from_address = self._resolve_from_address(request, context, runtime["from_address"])
        html_body, text_body = self._resolve_body(request, normalized_body, context)

        dispatched_count = len(recipients)
        metadata: Dict[str, Any] = {
            "from": from_address,
            "recipients": recipients,
            "subject": subject,
            "tool_context": context,
        }

        if not runtime["deliver"]:
            metadata["dry_run"] = True
            return PluginDispatchResult(
                plugin_name=self.name,
                dispatched_count=dispatched_count,
                failed=[],
                metadata=metadata,
            )

        if not runtime["api_key"]:
            raise RuntimeError("RESEND_API_KEY is not configured")

        resend.api_key = runtime["api_key"]
        params: Dict[str, Any] = {
            "from": from_address,
            "to": recipients,
            "subject": subject,
            "html": html_body,
        }
        if text_body:
            params["text"] = text_body

        extra_headers = context.get("headers")
        if isinstance(extra_headers, dict):
            params["headers"] = extra_headers

        cc = context.get("cc")
        if isinstance(cc, list):
            params["cc"] = [str(address).strip() for address in cc if str(address).strip()]

        bcc = context.get("bcc")
        if isinstance(bcc, list):
            params["bcc"] = [str(address).strip() for address in bcc if str(address).strip()]

        try:
            response = await asyncio.to_thread(resend.Emails.send, params)
        except Exception as exc:  # pragma: no cover - network failure path
            logger.exception("ResendEmailPlugin failed to deliver message: %s", exc)
            metadata["error"] = str(exc)
            return PluginDispatchResult(
                plugin_name=self.name,
                dispatched_count=0,
                failed=recipients,
                metadata=metadata,
            )

        message_id = None
        if isinstance(response, dict):
            message_id = response.get("id")
            metadata["resend_response"] = response
        else:
            message_id = getattr(response, "id", None)
            metadata["resend_response"] = getattr(response, "__dict__", {}) or str(response)

        if message_id:
            metadata["message_id"] = message_id

        return PluginDispatchResult(
            plugin_name=self.name,
            dispatched_count=dispatched_count,
            failed=[],
            metadata=metadata,
        )

    def _determine_recipients(
        self,
        request: OrchestrationRequest,
        context: Dict[str, Any],
        default_recipient: Optional[str],
    ) -> List[str]:
        audience = request.audience.recipients if request.audience else []
        payload = request.payload or {}
        metadata = request.metadata or {}

        recipients = list(audience)
        recipients.extend(payload.get("recipients", []))
        recipients.extend(payload.get("to", []))
        recipients.extend(metadata.get("recipients", []))
        recipients.extend(metadata.get("to", []))

        context_recipients = context.get("recipients")
        if isinstance(context_recipients, list):
            recipients.extend(context_recipients)

        if not recipients and default_recipient:
            recipients = [default_recipient]

        return _flatten_recipients(recipients)

    def _resolve_subject(
        self,
        request: OrchestrationRequest,
        context: Dict[str, Any],
        *,
        subject_hint: Optional[str] = None,
    ) -> str:
        payload = request.payload or {}
        metadata = request.metadata or {}

        subject = context.get("subject")
        if isinstance(subject, str) and subject.strip():
            return subject.strip()

        subject = payload.get("subject") or payload.get("title") or metadata.get("subject")
        if subject:
            return str(subject)
        if subject_hint and subject_hint.strip():
            return subject_hint.strip()
        return f"Kali Notification: {request.intent}".strip()

    def _resolve_from_address(
        self,
        request: OrchestrationRequest,
        context: Dict[str, Any],
        default_sender: Optional[str],
    ) -> str:
        metadata = request.metadata or {}
        from_context = context.get("from")
        if isinstance(from_context, str) and from_context.strip():
            return from_context.strip()
        from_metadata = metadata.get("from_address") or metadata.get("from")
        if isinstance(from_metadata, str) and from_metadata.strip():
            return from_metadata.strip()
        return default_sender or "no-reply@kali.local"

    def _resolve_body(
        self,
        request: OrchestrationRequest,
        rendered: str,
        context: Dict[str, Any],
    ) -> tuple[str, str | None]:
        payload = request.payload or {}
        html_body = context.get("html")
        text_body = context.get("text")

        if not isinstance(html_body, str) or not html_body.strip():
            payload_html = payload.get("html")
            if isinstance(payload_html, str) and payload_html.strip():
                html_body = payload_html.strip()
            else:
                html_body = _default_html_from_text(rendered)
        if not isinstance(text_body, str) or not text_body.strip():
            payload_text = payload.get("text")
            if isinstance(payload_text, str) and payload_text.strip():
                text_body = payload_text.strip()
            else:
                text_body = rendered.strip() or None
        return html_body, text_body

    def _resolve_runtime_config(self, defaults) -> Dict[str, Any]:
        env_api_key = os.getenv("RESEND_API_KEY")
        env_from = os.getenv("RESEND_FROM_ADDRESS")
        env_default_recipient = os.getenv("RESEND_DEFAULT_RECIPIENT")
        env_deliver = os.getenv("RESEND_DELIVER")

        api_key = (env_api_key or defaults.api_key or "").strip()
        from_address = (env_from or defaults.from_address or "no-reply@kali.local").strip()
        default_recipient = (env_default_recipient or defaults.default_recipient or "").strip() or None
        deliver = _coerce_bool(env_deliver) if env_deliver is not None else defaults.deliver

        return {
            "api_key": api_key,
            "from_address": from_address,
            "default_recipient": default_recipient,
            "deliver": deliver,
        }


def register_resend_plugin() -> None:
    plugin = ResendEmailPlugin()
    registry.register(plugin)
    registry.register_alias("email", plugin)
    registry.register_alias("resend", plugin)
    registry.register_alias("resend-email", plugin)
    registry.register_alias("smtp", plugin)
