from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from src.orchestration.models import OrchestrationRequest, PolicyDecision
from src.services.mongo_client import get_policy_collection

DirectiveLiteral = Literal["never_do", "notify_if"]


@dataclass
class PolicyDirective:
    """Represents a simple, user-provided policy instruction."""

    directive: DirectiveLiteral
    pattern: str

    def __post_init__(self) -> None:
        allowed_directives = {"never_do", "notify_if"}
        if self.directive not in allowed_directives:
            raise ValueError(f"Unsupported directive '{self.directive}'")
        cleaned = (self.pattern or "").strip().lower()
        if not cleaned:
            raise ValueError("Policy directive pattern must not be empty")
        self.pattern = cleaned

    def to_record(self) -> dict[str, str]:
        return {"directive": self.directive, "pattern": self.pattern}

    @classmethod
    def from_record(cls, record: dict[str, str]) -> PolicyDirective:
        return cls(directive=record.get("directive", ""), pattern=record.get("pattern", ""))


class PolicyStoreBackend(ABC):
    """Abstract base class for policy directive storage backends."""

    @abstractmethod
    def get_directives(self, tenant_id: str) -> list[PolicyDirective]:
        """Retrieve all policy directives for a given tenant."""
        pass

    @abstractmethod
    def add_directives(self, tenant_id: str, directives: Iterable[PolicyDirective]) -> list[PolicyDirective]:
        """Add new policy directives for a tenant. Returns list of successfully added directives."""
        pass

    @abstractmethod
    def summarize(self) -> dict[str, str]:
        """Return a summary of the backend state for diagnostics."""
        pass


class InMemoryPolicyStore(PolicyStoreBackend):
    """In-memory policy store implementation for testing and fallback scenarios."""

    def __init__(self) -> None:
        self._storage: dict[str, list[PolicyDirective]] = {}
        self._logger = logging.getLogger(__name__)

    def get_directives(self, tenant_id: str) -> list[PolicyDirective]:
        tenant_key = tenant_id or "default"
        return list(self._storage.get(tenant_key, []))

    def add_directives(self, tenant_id: str, directives: Iterable[PolicyDirective]) -> list[PolicyDirective]:
        tenant_key = tenant_id or "default"
        current = self._storage.get(tenant_key, [])

        added: list[PolicyDirective] = []
        for directive in directives:
            if directive not in current:
                current.append(directive)
                added.append(directive)

        self._storage[tenant_key] = current
        return added

    def summarize(self) -> dict[str, str]:
        total_directives = sum(len(items) for items in self._storage.values())
        return {"backend": "memory", "total_directives": str(total_directives)}


class MongoPolicyStore(PolicyStoreBackend):
    """MongoDB-backed policy store implementation with caching."""

    def __init__(self, collection=None) -> None:
        self._collection = collection if collection is not None else get_policy_collection()
        self._cache: dict[str, list[PolicyDirective]] = {}
        self._logger = logging.getLogger(__name__)

    def get_directives(self, tenant_id: str) -> list[PolicyDirective]:
        tenant_key = tenant_id or "default"

        # Check cache first
        cached = self._cache.get(tenant_key)
        if cached is not None:
            return list(cached)

        directives: list[PolicyDirective] = []
        if self._collection is not None:
            try:
                doc = self._collection.find_one(
                    {"tenant_id": tenant_key}, projection={"_id": False, "directives": True}
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                self._logger.warning("Failed to fetch policy directives from MongoDB: %s", exc)
                doc = None

            if doc and isinstance(doc.get("directives"), list):
                for entry in doc["directives"]:
                    if isinstance(entry, dict):
                        try:
                            directives.append(PolicyDirective.from_record(entry))
                        except ValueError:
                            continue

        self._cache[tenant_key] = directives
        return list(directives)

    def add_directives(self, tenant_id: str, directives: Iterable[PolicyDirective]) -> list[PolicyDirective]:
        tenant_key = tenant_id or "default"

        # Get current directives (from cache or database)
        current = self._cache.get(tenant_key)
        if current is None:
            current = self.get_directives(tenant_key)
        else:
            current = list(current)

        added: list[PolicyDirective] = []
        for directive in directives:
            if directive in current:
                continue

            current.append(directive)
            added.append(directive)

            # Persist to MongoDB if available
            if self._collection is not None:
                try:
                    self._collection.update_one(
                        {"tenant_id": tenant_key},
                        {
                            "$setOnInsert": {"tenant_id": tenant_key},
                            "$addToSet": {"directives": directive.to_record()},
                        },
                        upsert=True,
                    )
                except Exception as exc:  # pragma: no cover - defensive logging
                    self._logger.warning("Failed to persist directive to MongoDB: %s", exc)

        self._cache[tenant_key] = current
        return added

    def summarize(self) -> dict[str, str]:
        cached_directives = sum(len(items) for items in self._cache.values())
        return {
            "backend": "mongo",
            "cached_directives": str(cached_directives),
            "connected": str(self._collection is not None),
        }


class PolicyStore:
    """Facade that delegates to the appropriate backend implementation."""

    def __init__(self, backend: PolicyStoreBackend | None = None) -> None:
        if backend is None:
            backend = _create_default_backend()
        self._backend = backend

    def get_directives(self, tenant_id: str) -> list[PolicyDirective]:
        """Retrieve all policy directives for a given tenant."""
        return self._backend.get_directives(tenant_id)

    def add_directives(self, tenant_id: str, directives: Iterable[PolicyDirective]) -> list[PolicyDirective]:
        """Add new policy directives for a tenant. Returns list of successfully added directives."""
        return self._backend.add_directives(tenant_id, directives)

    def summarize(self) -> dict[str, str]:
        """Return a summary of the store state for diagnostics."""
        return self._backend.summarize()


class PolicyFeedbackAgent:
    """Extracts policy directives from user feedback and stores them."""

    _NEVER_PATTERN = re.compile(r"\bnever(?:\s+do)?\s+(?P<pattern>[^\.\!]+)", re.IGNORECASE)
    _NOTIFY_PATTERN = re.compile(r"\btell\s+me\s+if\s+(?P<pattern>[^\.\!]+)", re.IGNORECASE)

    def __init__(self, store: PolicyStore) -> None:
        self._store = store
        self._logger = logging.getLogger(__name__)

    def capture(self, request: OrchestrationRequest) -> list[PolicyDirective]:
        tenant_id = _resolve_tenant(request)
        instructions = self._extract_candidate_text(request)
        directives: list[PolicyDirective] = []

        for instruction in instructions:
            extracted = self._parse_instruction(instruction)
            directives.extend(extracted)

        if not directives:
            return []

        stored = self._store.add_directives(tenant_id, directives)
        if stored:
            self._logger.debug("Captured %s policy directives for %s", len(stored), tenant_id)
        return stored

    def _extract_candidate_text(self, request: OrchestrationRequest) -> list[str]:
        metadata = request.metadata or {}
        payload = request.payload or {}
        candidates: list[str] = []

        for key in ("policy_feedback", "user_policy_feedback", "user_directives"):
            value = metadata.get(key)
            candidates.extend(_normalize_text_source(value))

        payload_candidates = []
        for key in ("message", "text", "instructions"):
            payload_candidates.extend(_normalize_text_source(payload.get(key)))

        for text in payload_candidates:
            lowered = text.lower()
            if "never" in lowered or "tell me if" in lowered:
                candidates.append(text)

        return [text for text in (value.strip() for value in candidates) if text]

    def _parse_instruction(self, text: str) -> list[PolicyDirective]:
        directives: list[PolicyDirective] = []
        for pattern in self._NEVER_PATTERN.finditer(text):
            extracted = self._clean_pattern(pattern.group("pattern"))
            if extracted:
                try:
                    directives.append(PolicyDirective("never_do", extracted))
                except ValueError:
                    continue

        for pattern in self._NOTIFY_PATTERN.finditer(text):
            extracted = self._clean_pattern(pattern.group("pattern"))
            if extracted:
                try:
                    directives.append(PolicyDirective("notify_if", extracted))
                except ValueError:
                    continue

        return directives

    @staticmethod
    def _clean_pattern(pattern: str) -> str:
        cleaned = (pattern or "").strip().strip(".!")
        return cleaned


class PolicyEngine:
    """Evaluates orchestration requests against persisted policy directives."""

    def __init__(self, store: PolicyStore, policy_version: str | None = None) -> None:
        self._store = store
        self._policy_version = policy_version or "mongo/v1"

    def evaluate(self, request: OrchestrationRequest) -> PolicyDecision:
        tenant_id = _resolve_tenant(request)
        tags: set[str] = set()
        requires_human = False

        intent = request.intent.lower()
        if intent.startswith("escalate"):
            requires_human = True
            tags.add("escalation")

        metadata_priority = (request.metadata or {}).get("priority")
        if metadata_priority == "high":
            tags.add("priority:high")

        allowed = True
        reason = "Policy check passed"

        directives = self._store.get_directives(tenant_id)
        request_text = _flatten_request_text(request)

        for directive in directives:
            if directive.directive == "never_do" and directive.pattern in request_text:
                allowed = False
                requires_human = True
                reason = f"Blocked by directive '{directive.pattern}'"
                tags.add("policy:block")
                tags.add(f"policy:tenant:{tenant_id}")
                tags.add(f"policy:block:{directive.pattern.replace(' ', '_')}")
                break

        if allowed:
            for directive in directives:
                if directive.directive == "notify_if" and directive.pattern in request_text:
                    requires_human = True
                    tags.add("policy:notify")
                    tags.add(f"watch:{directive.pattern.replace(' ', '_')}")

            if requires_human:
                reason = "Requires human review before dispatch"

        return PolicyDecision(
            allowed=allowed,
            requires_human=requires_human,
            reason=reason,
            policy_version=self._policy_version,
            tags=sorted(tags),
        )

    def summarize(self) -> dict[str, str]:
        summary = {"policy_version": self._policy_version}
        summary.update(self._store.summarize())
        return summary


def _resolve_tenant(request: OrchestrationRequest) -> str:
    metadata = request.metadata or {}
    tenant = (
        metadata.get("tenant_id")
        or metadata.get("tenant")
        or metadata.get("workspace_id")
        or metadata.get("account_id")
        or "default"
    )
    return str(tenant)


def _normalize_text_source(value: object | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):  # type: ignore[arg-type]
        collected: list[str] = []
        for item in value:  # type: ignore[assignment]
            if isinstance(item, str):
                collected.append(item)
        return collected
    return []


def _flatten_request_text(request: OrchestrationRequest) -> str:
    parts: list[str] = [request.intent, request.channel or ""]

    def _flatten(value: object) -> Iterable[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            dict_items: list[str] = []
            for candidate in value.values():
                dict_items.extend(_flatten(candidate))
            return dict_items
        if isinstance(value, (list, tuple, set)):
            collection_items: list[str] = []
            for candidate in value:
                collection_items.extend(_flatten(candidate))
            return collection_items
        return [str(value)]

    parts.extend(_flatten(request.metadata))
    parts.extend(_flatten(request.payload))
    return " ".join(part.lower() for part in parts if part).strip()


def _create_default_backend() -> PolicyStoreBackend:
    """Create the default policy store backend based on MongoDB availability."""
    collection = get_policy_collection()
    if collection is not None:
        return MongoPolicyStore(collection)
    return InMemoryPolicyStore()


@lru_cache(maxsize=1)
def _get_policy_store() -> PolicyStore:
    return PolicyStore()


@lru_cache(maxsize=1)
def get_policy_engine() -> PolicyEngine:
    return PolicyEngine(_get_policy_store())


@lru_cache(maxsize=1)
def get_policy_feedback_agent() -> PolicyFeedbackAgent:
    return PolicyFeedbackAgent(_get_policy_store())
