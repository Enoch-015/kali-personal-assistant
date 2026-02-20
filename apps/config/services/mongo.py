"""MongoDB configuration settings."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class MongoSettings(BaseModel):
    """MongoDB connection and collection configuration."""

    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = Field(
        default=True,
        description="Enable MongoDB-backed policy storage when true.",
        validation_alias=AliasChoices("MONGO_ENABLED", "mongo_enabled"),
    )
    uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string used for policy persistence.",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI", "mongo_uri"),
    )
    database: str = Field(
        default="kali_policy",
        description="MongoDB database name for policy storage.",
        validation_alias=AliasChoices("MONGO_DATABASE", "mongo_database"),
    )
    policies_collection: str = Field(
        default="policy_directives",
        description="MongoDB collection used to persist policy directives.",
        validation_alias=AliasChoices("MONGO_POLICIES_COLLECTION", "mongo_policies_collection"),
    )
    server_selection_timeout_ms: int = Field(
        default=250,
        ge=50,
        le=10000,
        description="Timeout in milliseconds for selecting a MongoDB server.",
        validation_alias=AliasChoices(
            "MONGO_SERVER_SELECTION_TIMEOUT_MS",
            "mongo_server_selection_timeout_ms",
        ),
    )

    @classmethod
    def from_vault(cls, secrets: dict[str, Any]) -> "MongoSettings":
        """Build from Vault ``databases`` + ``python-ai`` secrets."""
        return cls(
            enabled=True,
            uri=secrets.get("mongodb-uri", "mongodb://localhost:27017"),
            database=secrets.get("mongodb-database", "kali_policy"),
            policies_collection=secrets.get("mongodb-policies-collection", "policy_directives"),
            server_selection_timeout_ms=int(
                secrets.get("mongodb-server-selection-timeout-ms", 250)
            ),
        )
