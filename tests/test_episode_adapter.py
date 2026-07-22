"""Tests for episode adapter (storage/retrieval with evidence metadata).

All tests run without external RuVector credentials.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from verdict.contracts import (
    OutcomeEvent,
    TaskSpec,
    TaskWorkflowOutcomeEpisode,
    WorkflowPlan,
)
from verdict.episode_adapter import (
    DuplicateEpisodeError,
    EpisodeNotFoundError,
    EpisodeSearchQuery,
    InMemoryEpisodeStore,
    RuVectorEpisodeStore,
    StorageDegradedError,
    StoreResult,
)


@pytest.fixture
def sample_episode() -> TaskWorkflowOutcomeEpisode:
    spec = TaskSpec(objective="test", task_type="coding")
    plan = WorkflowPlan(steps=[{"action": "research", "objective": "test"}])
    event = OutcomeEvent(
        event_type="finished",
        outcome="success",
        occurred_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    ep = TaskWorkflowOutcomeEpisode.from_contracts(
        task_spec=spec,
        workflow_plan=plan,
        outcome_event=event,
        episode_id="ep-test-1",
    )
    return TaskWorkflowOutcomeEpisode.from_dict(
        {
            **ep.to_dict(),
            "namespace": {"tenant": "verdict", "project": "core"},
            "embedding_version": "verdict-v1-redacted",
        }
    )


class TestInMemoryEpisodeStore:
    def test_store_and_retrieve(self, sample_episode):
        store = InMemoryEpisodeStore()
        stored = store.store(sample_episode)
        assert isinstance(stored, StoreResult)
        assert stored.episode_id == "ep-test-1"

        meta, ep = store.retrieve("ep-test-1")
        assert meta.episode_id == "ep-test-1"
        assert meta.namespace == {"tenant": "verdict", "project": "core"}
        assert meta.embedding_version == "verdict-v1-redacted"
        assert ep.episode_id == "ep-test-1"

    def test_store_generates_id_when_missing(self):
        store = InMemoryEpisodeStore()
        spec = TaskSpec(objective="test", task_type="coding")
        plan = WorkflowPlan(steps=[{"action": "research", "objective": "test"}])
        event = OutcomeEvent(event_type="test", outcome="test", occurred_at="2024-01-01T00:00:00Z")
        ep = TaskWorkflowOutcomeEpisode.from_contracts(
            task_spec=spec, workflow_plan=plan, outcome_event=event
        )
        stored = store.store(ep)
        assert stored.episode_id.startswith("ep-")

    def test_duplicate_detection(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)
        with pytest.raises(DuplicateEpisodeError):
            store.store(sample_episode)

    def test_retrieve_not_found(self):
        store = InMemoryEpisodeStore()
        with pytest.raises(EpisodeNotFoundError):
            store.retrieve("nonexistent")

    def test_retrieve_degraded(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)
        store.set_degraded()
        with pytest.raises(StorageDegradedError):
            store.retrieve("ep-test-1")

    def test_store_degraded(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.set_degraded()
        with pytest.raises(StorageDegradedError):
            store.store(sample_episode)

    def test_delete(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)
        store.delete("ep-test-1")
        with pytest.raises(EpisodeNotFoundError):
            store.retrieve("ep-test-1")

    def test_delete_not_found(self):
        store = InMemoryEpisodeStore()
        with pytest.raises(EpisodeNotFoundError):
            store.delete("nonexistent")

    def test_delete_degraded(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)
        store.set_degraded()
        with pytest.raises(StorageDegradedError):
            store.delete("ep-test-1")

    def test_search_by_tenant_and_project(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)

        results = store.search(EpisodeSearchQuery(tenant="verdict"))
        assert len(results) == 1

        results = store.search(EpisodeSearchQuery(tenant="other"))
        assert len(results) == 0

        results = store.search(EpisodeSearchQuery(tenant="verdict", project="core"))
        assert len(results) == 1

    def test_search_by_embedding_version(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)

        results = store.search(EpisodeSearchQuery(embedding_version="verdict-v1-redacted"))
        assert len(results) == 1

        results = store.search(EpisodeSearchQuery(embedding_version="v2"))
        assert len(results) == 0

    def test_search_limit_and_offset(self, sample_episode):
        store = InMemoryEpisodeStore()
        spec = TaskSpec(objective="test", task_type="coding")
        plan = WorkflowPlan(steps=[{"action": "research", "objective": "test"}])
        event = OutcomeEvent(event_type="test", outcome="test", occurred_at="2024-01-01T00:00:00Z")
        for i in range(5):
            ep = TaskWorkflowOutcomeEpisode.from_contracts(
                task_spec=spec,
                workflow_plan=plan,
                outcome_event=event,
                episode_id=f"ep-{i}",
            )
            store.store(ep)

        results = store.search(EpisodeSearchQuery(limit=3))
        assert len(results) == 3
        assert results[0].episode_id == "ep-0"

        results = store.search(EpisodeSearchQuery(limit=3, offset=2))
        assert len(results) == 3
        assert results[0].episode_id == "ep-2"

    def test_search_degraded_returns_empty(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)
        store.set_degraded()
        results = store.search(EpisodeSearchQuery(tenant="verdict"))
        assert results == []

    def test_search_max_age(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)
        # max_age < time since store -> should return results
        # Right after store, freshness is ~0 so any positive max_age allows it
        results = store.search(EpisodeSearchQuery(max_age_seconds=3600))
        assert len(results) == 1

    def test_available_property(self):
        store = InMemoryEpisodeStore()
        assert store.available is True
        store.set_degraded()
        assert store.available is False

    def test_capabilities_when_available(self):
        store = InMemoryEpisodeStore()
        assert "metadata_filter" in store.capabilities

    def test_capabilities_when_degraded(self):
        store = InMemoryEpisodeStore()
        store.set_degraded()
        assert store.capabilities == frozenset()

    def test_results_are_provenance_linked(self, sample_episode):
        store = InMemoryEpisodeStore()
        store.store(sample_episode)
        meta, _ = store.retrieve("ep-test-1")
        assert isinstance(meta.provenance, dict)
        # provenance was default factory so should exist
        assert isinstance(meta.namespace, dict)


class TestRuVectorEpisodeStore:
    def test_degraded_by_default(self):
        store = RuVectorEpisodeStore()
        assert store.available is False

    def test_store_raises_storage_degraded(self, sample_episode):
        store = RuVectorEpisodeStore()
        with pytest.raises(StorageDegradedError):
            store.store(sample_episode)

    def test_retrieve_raises_storage_degraded(self):
        store = RuVectorEpisodeStore()
        with pytest.raises(StorageDegradedError):
            store.retrieve("any")

    def test_delete_raises_storage_degraded(self):
        store = RuVectorEpisodeStore()
        with pytest.raises(StorageDegradedError):
            store.delete("any")

    def test_search_returns_empty(self, sample_episode):
        store = RuVectorEpisodeStore()
        results = store.search(EpisodeSearchQuery(tenant="verdict"))
        assert results == []

    def test_capabilities_empty_when_degraded(self):
        store = RuVectorEpisodeStore()
        assert store.capabilities == frozenset()
