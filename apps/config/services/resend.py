"""Resend email service configuration settings."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ResendSettings(BaseModel):
    """Resend email service configuration."""

    model_config = ConfigDict(populate_by_name=True)

    api_key: Optional[str] = Field(
        default=None,
        description="API key used for authenticating with Resend.",
        validation_alias=AliasChoices("RESEND_API_KEY", "resend_api_key"),
    )
    from_address: Optional[str] = Field(
        default="no-reply@kalienterprise.com",
        description="Default sender email address when none is provided in the request.",
        validation_alias=AliasChoices("RESEND_FROM_ADDRESS", "resend_from_address", "resend_from"),
    )
    default_recipient: Optional[str] = Field(
        default=None,
        description="Fallback recipient when a request omits recipients.",
        validation_alias=AliasChoices("RESEND_DEFAULT_RECIPIENT", "resend_default_recipient"),
    )
    deliver: bool = Field(
        default=False,
        description="Send messages via Resend when true; otherwise run in dry-run mode.",
        validation_alias=AliasChoices("RESEND_DELIVER", "resend_deliver"),
    )

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "ResendSettings":
        """Build from Vault ``shared`` secrets."""
        api_key = secrets.get("resend-api-key")
        deliver = secrets.get("resend-deliver", False)
        if isinstance(deliver, str):
            deliver = deliver.strip().lower() in {"1", "true", "yes", "on"}
        return cls(
            api_key=api_key,
            from_address=secrets.get("resend-from-address", "no-reply@kalienterprise.com"),
            default_recipient=secrets.get("resend-default-recipient"),
            deliver=bool(deliver) if api_key else False,
        )
