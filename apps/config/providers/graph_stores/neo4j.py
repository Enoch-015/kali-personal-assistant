"""Neo4j graph store settings."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseGraphStore


class Neo4jStore(BaseGraphStore):
    """Settings for a Neo4j graph database."""

    provider_name: ClassVar[str] = "neo4j"
    provider: Literal["neo4j"] = "neo4j"

    uri: Optional[str] = Field(default=None, description="Neo4j connection URI (bolt://…).")
    user: Optional[str] = Field(default=None, description="Neo4j username.")
    password: Optional[str] = Field(default=None, description="Neo4j password.")

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "Neo4jStore":
        return cls(
            uri=secrets.get("neo4j-uri") or secrets.get("neo4j_uri"),
            user=secrets.get("neo4j-username") or secrets.get("neo4j-user") or secrets.get("neo4j_user"),
            password=secrets.get("neo4j-password") or secrets.get("neo4j_password"),
        )

    @classmethod
    def from_env(cls, env: dict[str, Any]) -> "Neo4jStore":
        return cls(
            uri=env.get("neo4j_uri") or env.get("NEO4J_URI") or env.get("graphiti_neo4j_uri"),
            user=env.get("neo4j_user") or env.get("NEO4J_USER") or env.get("neo4j_username") or env.get("graphiti_neo4j_user"),
            password=env.get("neo4j_password") or env.get("NEO4J_PASSWORD") or env.get("graphiti_neo4j_password"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.uri and self.user and self.password)
