import sys
import types
from types import SimpleNamespace

import pytest

from config.settings import GraphitiSettings
from src.orchestration.memory import MemoryService
from src.orchestration.models import OrchestrationRequest
from src.services import graphiti_client as graphiti_module


class _DisabledGraphitiStub:
    def __init__(self) -> None:
        self.enabled = False
        self.default_group_id = None

    async def search_facts(self, *args, **kwargs):  # type: ignore[unused-argument]
        return []

    async def search_nodes(self, *args, **kwargs):  # type: ignore[unused-argument]
        return []

    async def record_memory_update(self, *args, **kwargs):  # type: ignore[unused-argument]
        return None


class _RecordingGraphitiStub:
    def __init__(self) -> None:
        self.enabled = True
        self.default_group_id = "default"
        self.recorded: list[dict] = []

    async def search_facts(self, query, **kwargs):  # type: ignore[unused-argument]
        return [f"fact:{query}"]

    async def search_nodes(self, query, **kwargs):  # type: ignore[unused-argument]
        return [f"node:{query}"]

    async def record_memory_update(self, **kwargs):
        self.recorded.append(kwargs)


@pytest.mark.asyncio
async def test_memory_service_falls_back_without_graphiti() -> None:
    service = MemoryService(graphiti_client=_DisabledGraphitiStub())
    request = OrchestrationRequest(intent="greet", channel="demo")

    snapshot = await service.retrieve_context(request)

    assert service.provider == "placeholder"
    assert any("greet" in snippet for snippet in snapshot.memory_snippets)
    assert snapshot.graph_relations[0].startswith("[demo]")


@pytest.mark.asyncio
async def test_memory_service_persists_updates_with_graphiti() -> None:
    graphiti = _RecordingGraphitiStub()
    service = MemoryService(graphiti_client=graphiti)
    request = OrchestrationRequest(intent="status", channel="email")

    snapshot = await service.retrieve_context(request)
    assert "fact:status" in snapshot.memory_snippets
    assert "node:status" in snapshot.graph_relations

    updates = service.prepare_updates(request, plugin_result=None, reflection="all good")
    await service.commit_updates(request, updates)

    assert len(graphiti.recorded) == 1
    payload = graphiti.recorded[0]
    assert payload["summary"] == "all good"
    assert payload["request_payload"]["intent"] == "status"


if "dotenv" not in sys.modules:  # pragma: no cover - testing convenience fallback
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.dotenv_values = lambda *args, **kwargs: {}  # type: ignore[arg-type]
    sys.modules["dotenv"] = dotenv_stub


@pytest.mark.asyncio
async def test_memory_service_with_configured_graphiti_client(monkeypatch) -> None:
    class DummyRecipe:
        def __init__(self, limit: int = 5) -> None:
            self.limit = limit

        def model_copy(self, deep: bool = True) -> "DummyRecipe":  # noqa: FBT001, FBT002
            return DummyRecipe(limit=self.limit)

    class DummyEpisodeType:
        text = "text"
        json = "json"

        @classmethod
        def __class_getitem__(cls, item: str) -> str:
            if item == "json":
                return cls.json
            if item == "text":
                return cls.text
            raise KeyError(item)

    class DummyGraphitiSDK:
        def __init__(self, uri: str, user: str, password: str, **kwargs) -> None:
            self.uri = uri
            self.user = user
            self.password = password
            self.kwargs = kwargs
            self.search_calls: list[dict[str, object]] = []
            self.node_calls: list[dict[str, object]] = []
            self.add_episode_calls: list[dict[str, object]] = []
            self.built_indices = False

        async def build_indices_and_constraints(self) -> None:
            self.built_indices = True

        async def search(self, **kwargs) -> list[SimpleNamespace]:
            self.search_calls.append(kwargs)
            query = kwargs.get("query", "unknown")
            return [SimpleNamespace(fact=f"fact:{query}")]

        async def _search(self, **kwargs) -> SimpleNamespace:
            self.node_calls.append(kwargs)
            query = kwargs.get("query", "unknown")
            node = SimpleNamespace(name="Entity", summary=f"Summary for {query}")
            return SimpleNamespace(nodes=[node])

        async def add_episode(self, **kwargs) -> None:
            self.add_episode_calls.append(kwargs)

        async def close(self) -> None:
            return None

    dummy_settings = type("DummySettings", (), {})()
    dummy_settings.graphiti = GraphitiSettings(
        enabled=True,
        llm_provider="openai",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        openai_api_key="sk-test",
        openai_model="gpt-4o",
        group_id="default-group",
        build_indices_on_startup=True,
        search_limit=2,
    )

    def graphiti_enabled_property(self: object) -> bool:  # type: ignore[explicit-override]
        return self.graphiti.enabled and self.graphiti.has_credentials

    type(dummy_settings).graphiti_enabled = property(graphiti_enabled_property)  # type: ignore[misc]

    monkeypatch.setattr(graphiti_module, "GraphitiSDK", DummyGraphitiSDK)
    monkeypatch.setattr(graphiti_module, "GraphitiEpisodeType", DummyEpisodeType)
    monkeypatch.setattr(graphiti_module, "NODE_HYBRID_SEARCH_RRF", DummyRecipe())
    graphiti_module.graphiti_client_singleton = None

    graphiti_client = graphiti_module.GraphitiClient(settings=dummy_settings)
    service = MemoryService(graphiti_client=graphiti_client)
    request = OrchestrationRequest(intent="status", channel="email")

    snapshot = await service.retrieve_context(request)

    assert service.provider == "graphiti"
    assert snapshot.memory_snippets == ["fact:status"]
    assert snapshot.graph_relations[0].startswith("Entity: Summary for status")

    client_instance = graphiti_client._client  # type: ignore[attr-defined]
    assert isinstance(client_instance, DummyGraphitiSDK)
    assert client_instance.built_indices is True
    assert client_instance.search_calls and client_instance.search_calls[0]["group_id"] == "default-group"
    assert client_instance.kwargs == {}

    updates = service.prepare_updates(request, plugin_result=None, reflection="sync complete")
    await service.commit_updates(request, updates)

    assert len(client_instance.add_episode_calls) == 1
    call = client_instance.add_episode_calls[0]
    assert call["group_id"] == "default-group"
    assert call["name"].startswith("memory::")
