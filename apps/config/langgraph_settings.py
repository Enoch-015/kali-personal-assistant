"""LangGraph orchestration configuration settings."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LangGraphSettings(BaseModel):
    """LangGraph checkpoint and concurrency configuration."""
    
    checkpoint_store: Literal["memory", "sqlite"] = Field(default="memory")
    checkpoint_path: str = Field(
        default=".langgraph/checkpoints.sqlite",
        description="Path used when checkpoint_store is set to 'sqlite'.",
    )
    max_concurrency: int = Field(default=32, ge=1, le=256)
