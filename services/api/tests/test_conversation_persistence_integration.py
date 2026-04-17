from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://sovrn:devpassword@localhost:5432/sovrn")

from app.api.v1.endpoints import ai  # noqa: E402
from app.services.conversation_repository import ConversationVersionConflictError  # noqa: E402


@dataclass(slots=True)
class _ThreadRecord:
    id: UUID
    user_id: UUID
    project_id: UUID | None
    state_version: int = 1
    authoritative_state: dict[str, Any] = field(default_factory=dict)
    locked_constraints: list[Any] = field(default_factory=list)
    last_turn_index: int = 0


@dataclass(slots=True)
class _TurnRecord:
    id: UUID
    thread_id: UUID
    turn_index: int
    idempotency_key: str


@dataclass(slots=True)
class _SummaryRecord:
    thread_id: UUID
    from_turn_index: int
    to_turn_index: int
    summary_json: dict[str, Any]


@dataclass(slots=True)
class _Store:
    threads: dict[UUID, _ThreadRecord] = field(default_factory=dict)
    turns_by_idempotency: dict[tuple[UUID, str], _TurnRecord] = field(default_factory=dict)
    summaries: list[_SummaryRecord] = field(default_factory=list)
    create_thread_calls: int = 0
    append_turn_calls: int = 0
    summary_writes: int = 0
    raise_version_conflict: bool = False


class _FakeDB:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _build_ai_response(content: str = "Acknowledged") -> SimpleNamespace:
    return SimpleNamespace(
        content=content,
        provider=SimpleNamespace(value="mock"),
        model="mock-model",
        success=True,
        latency_ms=12,
        tokens_used=42,
    )


def _build_chat_request(
    *,
    user_id: UUID,
    thread_id: UUID | None = None,
    idempotency_key: str,
) -> ai.ChatRequest:
    return ai.ChatRequest(
        messages=[
            ai.ChatMessage(
                role="user",
                content="Build a modern SaaS landing page with pricing and FAQ.",
            )
        ],
        user_id=user_id,
        thread_id=thread_id,
        idempotency_key=idempotency_key,
    )


def _install_persistence_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    raise_version_conflict: bool = False,
    summarization_enabled: bool = False,
    summary_trigger_turns: int = 6,
) -> tuple[_Store, _FakeDB]:
    store = _Store(raise_version_conflict=raise_version_conflict)
    db = _FakeDB()

    class _AsyncSessionContext:
        async def __aenter__(self) -> _FakeDB:
            return db

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    def _fake_async_session() -> _AsyncSessionContext:
        return _AsyncSessionContext()

    class _FakeConversationRepository:
        def __init__(self, _db: _FakeDB):
            self.db = _db

        async def create_thread(
            self,
            *,
            user_id: UUID,
            project_id: UUID | None = None,
            status: str = "active",
            authoritative_state: dict[str, Any] | None = None,
            locked_constraints: list[Any] | None = None,
        ) -> _ThreadRecord:
            _ = status
            store.create_thread_calls += 1
            thread = _ThreadRecord(
                id=uuid4(),
                user_id=user_id,
                project_id=project_id,
                authoritative_state=authoritative_state or {},
                locked_constraints=locked_constraints or [],
            )
            store.threads[thread.id] = thread
            return thread

        async def get_thread(self, thread_id: UUID) -> _ThreadRecord | None:
            return store.threads.get(thread_id)

        async def get_turn_by_idempotency_key(
            self,
            *,
            thread_id: UUID,
            idempotency_key: str,
        ) -> _TurnRecord | None:
            return store.turns_by_idempotency.get((thread_id, idempotency_key))

        async def append_turn(
            self,
            *,
            thread_id: UUID,
            turn_index: int,
            user_message: str,
            idempotency_key: str,
            server_response: dict[str, Any] | None = None,
            model_raw_output: dict[str, Any] | None = None,
            parse_status: str = "not_attempted",
            provider: str | None = None,
            model: str | None = None,
            latency_ms: int | None = None,
            tokens_used: int | None = None,
        ) -> _TurnRecord:
            _ = (
                user_message,
                server_response,
                model_raw_output,
                parse_status,
                provider,
                model,
                latency_ms,
                tokens_used,
            )
            existing = store.turns_by_idempotency.get((thread_id, idempotency_key))
            if existing is not None:
                return existing

            store.append_turn_calls += 1
            turn = _TurnRecord(
                id=uuid4(),
                thread_id=thread_id,
                turn_index=turn_index,
                idempotency_key=idempotency_key,
            )
            store.turns_by_idempotency[(thread_id, idempotency_key)] = turn
            return turn

        async def write_state_snapshot(
            self,
            *,
            thread_id: UUID,
            expected_version: int,
            authoritative_state: dict[str, Any],
            locked_constraints: list[Any],
            turn_id: UUID | None = None,
            last_turn_index: int | None = None,
        ) -> SimpleNamespace:
            _ = turn_id
            thread = store.threads[thread_id]
            if store.raise_version_conflict:
                raise ConversationVersionConflictError(
                    thread_id=thread_id,
                    expected_version=expected_version,
                    current_version=expected_version + 1,
                )

            if thread.state_version != expected_version:
                raise ConversationVersionConflictError(
                    thread_id=thread_id,
                    expected_version=expected_version,
                    current_version=thread.state_version,
                )

            thread.state_version += 1
            thread.authoritative_state = dict(authoritative_state)
            thread.locked_constraints = list(locked_constraints)
            if last_turn_index is not None:
                thread.last_turn_index = last_turn_index

            return SimpleNamespace(state_version=thread.state_version)

        async def get_latest_summary(self, thread_id: UUID):
            candidates = [summary for summary in store.summaries if summary.thread_id == thread_id]
            if not candidates:
                return None
            return max(candidates, key=lambda summary: summary.to_turn_index)

        async def write_summary(
            self,
            *,
            thread_id: UUID,
            from_turn_index: int,
            to_turn_index: int,
            summary_json: dict[str, Any],
            summarizer_version: str | None = None,
            quality_score: float | None = None,
        ) -> _SummaryRecord:
            _ = (summarizer_version, quality_score)
            store.summary_writes += 1
            record = _SummaryRecord(
                thread_id=thread_id,
                from_turn_index=from_turn_index,
                to_turn_index=to_turn_index,
                summary_json=dict(summary_json),
            )
            store.summaries.append(record)
            return record

    monkeypatch.setattr(ai.settings, "AI_STATE_PERSIST_ENABLED", True)
    monkeypatch.setattr(ai.settings, "AI_SUMMARIZATION_ENABLED", summarization_enabled)
    monkeypatch.setattr(ai.settings, "AI_SUMMARY_TRIGGER_EVERY_TURNS", summary_trigger_turns)
    monkeypatch.setattr(ai, "async_session", _fake_async_session)
    monkeypatch.setattr(ai, "ConversationRepository", _FakeConversationRepository)
    return store, db


@pytest.mark.asyncio
async def test_idempotent_replay_by_thread_and_key(monkeypatch: pytest.MonkeyPatch) -> None:
    store, db = _install_persistence_harness(monkeypatch)
    user_id = uuid4()
    response = _build_ai_response()

    first_request = _build_chat_request(
        user_id=user_id,
        idempotency_key="idem-replay-0001",
    )
    first_meta = await ai._persist_conversation_shadow_state(first_request, response)

    assert first_meta is not None
    replay_request = _build_chat_request(
        user_id=user_id,
        thread_id=UUID(first_meta["thread_id"]),
        idempotency_key="idem-replay-0001",
    )
    replay_meta = await ai._persist_conversation_shadow_state(replay_request, response)

    assert replay_meta is not None
    assert replay_meta["thread_id"] == first_meta["thread_id"]
    assert replay_meta["turn_index"] == first_meta["turn_index"]
    assert replay_meta["idempotency_key"] == first_meta["idempotency_key"]
    assert store.append_turn_calls == 1
    assert db.commits == 1
    assert db.rollbacks == 1


@pytest.mark.asyncio
async def test_resume_existing_thread_vs_create_new_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    store, db = _install_persistence_harness(monkeypatch)
    user_id = uuid4()
    response = _build_ai_response("Continuing thread")

    first_request = _build_chat_request(
        user_id=user_id,
        idempotency_key="idem-resume-0001",
    )
    first_meta = await ai._persist_conversation_shadow_state(first_request, response)
    assert first_meta is not None

    second_request = _build_chat_request(
        user_id=user_id,
        thread_id=UUID(first_meta["thread_id"]),
        idempotency_key="idem-resume-0002",
    )
    second_meta = await ai._persist_conversation_shadow_state(second_request, response)

    assert second_meta is not None
    assert second_meta["thread_id"] == first_meta["thread_id"]
    assert second_meta["turn_index"] == 2
    assert second_meta["state_version"] == 3
    assert store.create_thread_calls == 1
    assert store.append_turn_calls == 2
    assert db.commits == 2


@pytest.mark.asyncio
async def test_snapshot_version_conflict_is_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    store, db = _install_persistence_harness(monkeypatch, raise_version_conflict=True)
    user_id = uuid4()
    response = _build_ai_response("Conflict path")

    request = _build_chat_request(
        user_id=user_id,
        idempotency_key="idem-conflict-0001",
    )
    metadata = await ai._persist_conversation_shadow_state(request, response)

    assert metadata is None
    assert store.create_thread_calls == 1
    assert store.append_turn_calls == 1
    assert db.commits == 0
    assert db.rollbacks == 0


@pytest.mark.asyncio
async def test_compaction_summary_trigger_respects_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    store, db = _install_persistence_harness(
        monkeypatch,
        summarization_enabled=True,
        summary_trigger_turns=3,
    )
    user_id = uuid4()
    response = _build_ai_response("Threshold path")

    first_meta = await ai._persist_conversation_shadow_state(
        _build_chat_request(user_id=user_id, idempotency_key="idem-threshold-0001"),
        response,
    )
    assert first_meta is not None

    thread_id = UUID(first_meta["thread_id"])
    await ai._persist_conversation_shadow_state(
        _build_chat_request(
            user_id=user_id,
            thread_id=thread_id,
            idempotency_key="idem-threshold-0002",
        ),
        response,
    )
    assert store.summary_writes == 0

    await ai._persist_conversation_shadow_state(
        _build_chat_request(
            user_id=user_id,
            thread_id=thread_id,
            idempotency_key="idem-threshold-0003",
        ),
        response,
    )

    assert store.summary_writes == 1
    latest_summary = store.summaries[-1]
    assert latest_summary.from_turn_index == 1
    assert latest_summary.to_turn_index == 3
    assert db.commits == 3


@pytest.mark.asyncio
async def test_invalid_summary_payload_is_rejected_without_persist_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, db = _install_persistence_harness(
        monkeypatch,
        summarization_enabled=True,
        summary_trigger_turns=1,
    )
    user_id = uuid4()
    response = _build_ai_response("Invalid summary payload")

    monkeypatch.setattr(
        ai,
        "parse_conversation_summary_output",
        lambda _payload: SimpleNamespace(success=False, parsed=None, error="invalid-summary"),
    )

    metadata = await ai._persist_conversation_shadow_state(
        _build_chat_request(user_id=user_id, idempotency_key="idem-invalid-summary-0001"),
        response,
    )

    assert metadata is not None
    assert store.summary_writes == 0
    assert db.commits == 1
