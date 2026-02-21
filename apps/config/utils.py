"""Utility functions for settings coercion and validation."""

from __future__ import annotations

from typing import Any


def coerce_bool(value: Any) -> bool:
    """Coerce a value to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
    return bool(value)


def coerce_str(value: Any) -> str:
    """Coerce a value to string."""
    return str(value).strip()


def coerce_int(value: Any) -> int:
    """Coerce a value to integer."""
    return int(str(value))
