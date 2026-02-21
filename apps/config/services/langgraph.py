"""LangGraph orchestration configuration settings."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LangGraphSettings(BaseModel):
    """LangGraph checkpoint and concurrency configuration."""

    checkpoint_store: Literal["memory", "sqlite"] = Field(default="memory")
    checkpoint_path: str = Field(
        default=".langgraph/checkpoints.sqlite",
        description="Path used when checkpoint_store is set to 'sqlite'.",
    )
    max_concurrency: int = Field(default=32, ge=1, le=256)

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "LangGraphSettings":
        """Build from Vault ``python-ai`` secrets."""
        store = secrets.get("langgraph-checkpoint-store", "memory")
        if store not in ("memory", "sqlite"):
            store = "memory"
        return cls(
            checkpoint_store=store,  # type: ignore[arg-type]
            checkpoint_path=secrets.get(
                "langgraph-checkpoint-path",
                ".langgraph/checkpoints.sqlite",
            ),
            max_concurrency=int(secrets.get("langgraph-max-concurrency", 32)),
        )
