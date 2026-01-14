"""Resend email service configuration settings."""

from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, BaseModel, Field


class ResendSettings(BaseModel):
    """Resend email service configuration."""
    
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
