from __future__ import annotations

import logging
from typing import Optional

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
except Exception:  # pragma: no cover - dependency import guard
    MongoClient = None  # type: ignore
    Collection = None  # type: ignore

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_client: Optional[MongoClient] = None


def _connect() -> Optional[MongoClient]:
    settings = get_settings()
    mongo_settings = getattr(settings, "mongo", None)
    if not mongo_settings or not mongo_settings.enabled:
        return None
    if MongoClient is None:
        logger.warning("pymongo is not available; falling back to in-memory policy store")
        return None
    try:
        client = MongoClient(
            mongo_settings.uri,
            serverSelectionTimeoutMS=mongo_settings.server_selection_timeout_ms,
        )
        client.admin.command("ping")
    except Exception as exc:  # pragma: no cover - network failure path
        logger.warning("MongoDB connection unavailable: %s", exc)
        return None
    return client


def get_mongo_client() -> Optional[MongoClient]:
    global _client
    if _client is not None:
        return _client
    _client = _connect()
    return _client


def get_policy_collection() -> Optional[Collection]:
    client = get_mongo_client()
    if client is None or Collection is None:
        return None
    settings = get_settings()
    mongo_settings = getattr(settings, "mongo", None)
    if not mongo_settings:
        return None
    try:
        database = client[mongo_settings.database]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("MongoDB database unavailable: %s", exc)
        return None
    try:
        return database[mongo_settings.policies_collection]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("MongoDB collection unavailable: %s", exc)
        return None
