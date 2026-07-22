"""Replaceable episode storage adapter with evidence metadata.

Provides abstract interfaces and in-memory fake for storing and
retrieving privacy-safe execution episodes (TaskWorkflowOutcomeEpisode)
with support for metadata filtering, tenant isolation, and embedding
version gating.
"""

from __future__ import annotations

import abc
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from verdict.contracts import TaskWorkflowOutcomeEpisode


class EpisodeStorageError(Exception):
    """Base error for episode storage operations."""


class EpisodeNotFoundError(EpisodeStorageError):
    """Raised when a requested episode_id does not exist."""


class DuplicateEpisodeError(EpisodeStorageError):
    """Raised when an episode with a conflict is stored."""


class StorageDegradedError(EpisodeStorageError):
    """Raised when the storage adapter is unavailable or degraded.
    This must never block deterministic routing safety; callers should
    treat a StorageDegradedError as a non-fatal warning and continue
    without storage.
    """


@dataclass(frozen=True)
class RetrievalResult:
    """Evidence metadata returned with every retrieval result."""

    episode_id: str
    score: float = 0.0
    freshness_seconds: float = 0.0
    provenance: dict[str, Any] = field(default_factory=dict)
    namespace: dict[str, Any] = field(default_factory=dict)
    embedding_version: str = "none"


@dataclass(frozen=True)
class StoreResult:
    """Result of a store operation."""

    episode_id: str
    stored_at: str


@dataclass(frozen=True)
class EpisodeSearchQuery:
    """Structured query for episode retrieval."""

    tenant: str | None = None
    project: str | None = None
    embedding_version: str | None = None
    max_age_seconds: float | None = None
    limit: int = 20
    offset: int = 0


class EpisodeStore(abc.ABC):
    """Abstract episode storage adapter.
    All concrete implementations must be replaceable without changing
    callers. Adapter absence (StorageDegradedError) must not block
    deterministic routing safety.
    """

    @property
    @abc.abstractmethod
    def available(self) -> bool:
        """Whether the adapter is functional."""

    @property
    @abc.abstractmethod
    def capabilities(self) -> frozenset[str]:
        """Set of supported capabilities."""

    @abc.abstractmethod
    def store(
        self,
        episode: TaskWorkflowOutcomeEpisode,
    ) -> StoreResult:
        """Persist an episode and return its storage metadata."""

    @abc.abstractmethod
    def retrieve(
        self,
        episode_id: str,
    ) -> tuple[RetrievalResult, TaskWorkflowOutcomeEpisode]:
        """Retrieve a stored episode by its storage key."""

    @abc.abstractmethod
    def delete(self, episode_id: str) -> None:
        """Remove a stored episode."""

    @abc.abstractmethod
    def search(
        self,
        query: EpisodeSearchQuery,
    ) -> Sequence[RetrievalResult]:
        """Search episodes with metadata filtering."""

    def redact_before_persist(self, episode: TaskWorkflowOutcomeEpisode) -> dict[str, Any]:
        raise NotImplementedError("not implemented")


class InMemoryEpisodeStore(EpisodeStore):
    """Deterministic in-memory fake for testing.
    Does not require external credentials or RuVector.
    """

    def __init__(self) -> None:
        self._records: dict[str, TaskWorkflowOutcomeEpisode] = OrderedDict()
        self._timestamps: dict[str, float] = {}
        self._available = True

    @property
    def available(self) -> bool:
        return self._available

    @available.setter
    def available(self, value: bool) -> None:
        self._available = value

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({"metadata_filter"}) if self._available else frozenset()

    def set_degraded(self) -> None:
        """Simulate adapter degradation for testing."""
        self._available = False

    def store(self, episode: TaskWorkflowOutcomeEpisode) -> StoreResult:
        if not self._available:
            raise StorageDegradedError("store unavailable")
        ep_id = episode.episode_id or f"ep-{uuid4().hex}"
        if ep_id in self._records:
            existing = self._records[ep_id]
            if existing.embedding_version == episode.embedding_version:
                raise DuplicateEpisodeError(f"duplicate episode {ep_id}")
        now = _now()
        self._records[ep_id] = episode
        self._timestamps[ep_id] = now
        return StoreResult(episode_id=ep_id, stored_at=_epoch_to_iso(now))

    def retrieve(self, episode_id: str) -> tuple[RetrievalResult, TaskWorkflowOutcomeEpisode]:
        if not self._available:
            raise StorageDegradedError("retrieve unavailable")
        episode = self._records.get(episode_id)
        if episode is None:
            raise EpisodeNotFoundError(f"episode not found: {episode_id}")
        stored_at = self._timestamps.get(episode_id, 0.0)
        return RetrievalResult(
            episode_id=episode_id,
            freshness_seconds=_now() - stored_at,
            provenance=episode.provenance,
            namespace=episode.namespace,
            embedding_version=episode.embedding_version or "none",
        ), episode

    def delete(self, episode_id: str) -> None:
        if not self._available:
            raise StorageDegradedError("delete unavailable")
        if episode_id not in self._records:
            raise EpisodeNotFoundError(f"episode not found: {episode_id}")
        del self._records[episode_id]
        self._timestamps.pop(episode_id, None)

    def search(self, query: EpisodeSearchQuery) -> Sequence[RetrievalResult]:
        if not self._available:
            return []
        now = _now()
        results: list[RetrievalResult] = []
        for idx, (ep_id, episode) in enumerate(self._records.items()):
            if idx < query.offset:
                continue
            if len(results) >= query.limit:
                break
            if not self._matches(ep_id, episode, query, now):
                continue
            stored_at = self._timestamps.get(ep_id, now)
            results.append(
                RetrievalResult(
                    episode_id=ep_id,
                    freshness_seconds=now - stored_at,
                    provenance=episode.provenance,
                    namespace=episode.namespace,
                    embedding_version=episode.embedding_version or "none",
                )
            )
        return results

    def _matches(
        self,
        ep_id: str,
        episode: TaskWorkflowOutcomeEpisode,
        query: EpisodeSearchQuery,
        now: float,
    ) -> bool:
        if query.tenant and episode.namespace.get("tenant") != query.tenant:
            return False
        if query.project and episode.namespace.get("project") != query.project:
            return False
        if query.embedding_version is not None:  # noqa: SIM102
            if episode.embedding_version != query.embedding_version:
                return False
        if query.max_age_seconds is not None:
            stored_at = self._timestamps.get(ep_id)
            if stored_at is None or (now - stored_at) > query.max_age_seconds:
                return False
        return True


class RuVectorEpisodeStore(EpisodeStore):
    """RuVector-backed episode storage (placeholder stub).
    Degraded by default; no credentials required.
    """

    def __init__(self) -> None:
        self._available = False

    @property
    def available(self) -> bool:
        return self._available

    @property
    def capabilities(self) -> frozenset[str]:
        return (
            frozenset()
            if not self._available
            else frozenset({"vector", "bm25", "hybrid", "mmr", "metadata_filter"})
        )

    def store(self, episode: TaskWorkflowOutcomeEpisode) -> StoreResult:
        raise StorageDegradedError("RuVector adapter not yet available")

    def retrieve(self, episode_id: str) -> tuple[RetrievalResult, TaskWorkflowOutcomeEpisode]:
        raise StorageDegradedError("RuVector adapter not yet available")

    def delete(self, episode_id: str) -> None:
        raise StorageDegradedError("RuVector adapter not yet available")

    def search(self, query: EpisodeSearchQuery) -> Sequence[RetrievalResult]:
        return []


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def _epoch_to_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "DuplicateEpisodeError",
    "EpisodeNotFoundError",
    "EpisodeSearchQuery",
    "EpisodeStorageError",
    "EpisodeStore",
    "InMemoryEpisodeStore",
    "RetrievalResult",
    "RuVectorEpisodeStore",
    "StorageDegradedError",
    "StoreResult",
]
