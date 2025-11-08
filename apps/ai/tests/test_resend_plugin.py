import pytest
import resend

from src.orchestration.models import OrchestrationRequest
from src.orchestration.plugins.resend_email import ResendEmailPlugin


@pytest.mark.asyncio
async def test_resend_plugin_dry_run_uses_context() -> None:
    plugin = ResendEmailPlugin()
    request = OrchestrationRequest(intent="status_update", channel="email")

    result = await plugin.dispatch(
        request,
        "Status: Active",
        context={
            "subject": "Project Status Update",
            "recipients": ["user@example.com"],
            "html": "<strong>Status: Active</strong>",
            "text": "Status: Active",
        },
    )

    assert result.plugin_name == "resend-email"
    assert result.dispatched_count == 1
    assert result.failed == []
    assert result.metadata.get("dry_run") is True
    assert result.metadata.get("subject") == "Project Status Update"
    assert result.metadata.get("recipients") == ["user@example.com"]
    assert "tool_context" in result.metadata


@pytest.mark.asyncio
async def test_resend_plugin_prefers_env_for_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEND_DEFAULT_RECIPIENT", "env-user@example.com")
    monkeypatch.setenv("RESEND_FROM_ADDRESS", "Env Sender <env@example.com>")
    monkeypatch.setenv("RESEND_DELIVER", "false")

    plugin = ResendEmailPlugin()
    request = OrchestrationRequest(intent="status_update", channel="email")

    result = await plugin.dispatch(request, "Status: Pending", context={})

    assert result.metadata.get("recipients") == ["env-user@example.com"]
    assert result.metadata.get("from") == "Env Sender <env@example.com>"
    assert result.metadata.get("dry_run") is True


@pytest.mark.asyncio
async def test_resend_plugin_extracts_subject_from_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEND_DELIVER", "true")
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("RESEND_FROM_ADDRESS", "sender@example.com")

    captured: dict = {}

    def fake_send(params):
        captured.update(params)
        return {"id": "test-message"}

    monkeypatch.setattr(resend.Emails, "send", fake_send)

    plugin = ResendEmailPlugin()
    request = OrchestrationRequest(
        intent="Send a status update email to oshinfowokan.oluwaseyifunmi@lmu.edu.ng",
        channel="email",
    )

    message = (
        "Subject: Status Update\n\n"
        "Dear Oluwaseyifunmi,\n\n"
        "We are pleased to inform you that your current status is: Active.\n\n"
        "Best regards,\n\n"
        "Kali Team"
    )

    await plugin.dispatch(
        request,
        message,
        context={"recipients": ["oshinfowokan.oluwaseyifunmi@lmu.edu.ng"]},
    )

    assert captured.get("subject") == "Status Update"
    assert "Subject:" not in captured.get("html", "")
    assert captured.get("text") == (
        "Dear Oluwaseyifunmi,\n\n"
        "We are pleased to inform you that your current status is: Active.\n\n"
        "Best regards,\n\n"
        "Kali Team"
    )
