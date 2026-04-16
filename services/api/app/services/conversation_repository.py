"""Conversation persistence repository.

Provides minimal data access helpers for conversation thread, turn, snapshot,
and summary records. Endpoint wiring is intentionally out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ConversationStateSnapshot,
    ConversationSummary,
    ConversationThread,
    ConversationTurn,
)


class ConversationRepositoryError(RuntimeError):
    """Base class for conversation repository errors."""


@dataclass(slots=True)
class ConversationVersionConflictError(ConversationRepositoryError):
    """Raised when optimistic state version check fails."""

    thread_id: UUID
    expected_version: int
    current_version: int

    def __str__(self) -> str:
        return (
            f"Conversation state version conflict for thread {self.thread_id}: "
            f"expected={self.expected_version}, current={self.current_version}"
        )


class ConversationThreadNotFoundError(ConversationRepositoryError):
    """Raised when a conversation thread cannot be found."""


class ConversationRepository:
    """Repository for conversation persistence tables."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_thread(
        self,
        *,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        status: str = "active",
        authoritative_state: Optional[dict[str, Any]] = None,
        locked_constraints: Optional[list[Any]] = None,
    ) -> ConversationThread:
        thread = ConversationThread(
            user_id=user_id,
            project_id=project_id,
            status=status,
            state_version=1,
            authoritative_state=authoritative_state or {},
            locked_constraints=locked_constraints or [],
            last_turn_index=0,
        )
        self.db.add(thread)
        await self.db.flush()
        await self.db.refresh(thread)
        return thread

    async def get_thread(self, thread_id: UUID) -> Optional[ConversationThread]:
        result = await self.db.execute(
            select(ConversationThread).where(ConversationThread.id == thread_id)
        )
        return result.scalar_one_or_none()

    async def append_turn(
        self,
        *,
        thread_id: UUID,
        turn_index: int,
        user_message: str,
        idempotency_key: str,
        server_response: Optional[dict[str, Any]] = None,
        model_raw_output: Optional[dict[str, Any]] = None,
        parse_status: str = "not_attempted",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        latency_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
    ) -> ConversationTurn:
        existing = await self.get_turn_by_idempotency_key(
            thread_id=thread_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing

        turn = ConversationTurn(
            thread_id=thread_id,
            turn_index=turn_index,
            user_message=user_message,
            model_raw_output=model_raw_output,
            server_response=server_response or {},
            parse_status=parse_status,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            idempotency_key=idempotency_key,
        )
        self.db.add(turn)
        await self.db.flush()
        await self.db.refresh(turn)
        return turn

    async def get_turn_by_idempotency_key(
        self,
        *,
        thread_id: UUID,
        idempotency_key: str,
    ) -> Optional[ConversationTurn]:
        result = await self.db.execute(
            select(ConversationTurn).where(
                ConversationTurn.thread_id == thread_id,
                ConversationTurn.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_recent_turns(
        self,
        *,
        thread_id: UUID,
        limit: int,
    ) -> list[ConversationTurn]:
        result = await self.db.execute(
            select(ConversationTurn)
            .where(ConversationTurn.thread_id == thread_id)
            .order_by(ConversationTurn.turn_index.desc())
            .limit(limit)
        )
        turns = list(result.scalars().all())
        turns.reverse()
        return turns

    async def write_state_snapshot(
        self,
        *,
        thread_id: UUID,
        expected_version: int,
        authoritative_state: dict[str, Any],
        locked_constraints: list[Any],
        turn_id: Optional[UUID] = None,
        last_turn_index: Optional[int] = None,
    ) -> ConversationStateSnapshot:
        result = await self.db.execute(
            select(ConversationThread)
            .where(ConversationThread.id == thread_id)
            .with_for_update()
        )
        thread = result.scalar_one_or_none()
        if thread is None:
            raise ConversationThreadNotFoundError(f"Conversation thread not found: {thread_id}")

        current_version = int(thread.state_version)
        if current_version != expected_version:
            raise ConversationVersionConflictError(
                thread_id=thread_id,
                expected_version=expected_version,
                current_version=current_version,
            )

        new_version = current_version + 1
        thread.state_version = new_version
        thread.authoritative_state = authoritative_state
        thread.locked_constraints = locked_constraints
        if last_turn_index is not None:
            thread.last_turn_index = last_turn_index

        snapshot = ConversationStateSnapshot(
            thread_id=thread_id,
            turn_id=turn_id,
            state_version=new_version,
            authoritative_state=authoritative_state,
            locked_constraints=locked_constraints,
        )
        self.db.add(snapshot)
        await self.db.flush()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_latest_state_snapshot(self, thread_id: UUID) -> Optional[ConversationStateSnapshot]:
        result = await self.db.execute(
            select(ConversationStateSnapshot)
            .where(ConversationStateSnapshot.thread_id == thread_id)
            .order_by(ConversationStateSnapshot.state_version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def write_summary(
        self,
        *,
        thread_id: UUID,
        from_turn_index: int,
        to_turn_index: int,
        summary_json: dict[str, Any],
        summarizer_version: Optional[str] = None,
        quality_score: Optional[float] = None,
    ) -> ConversationSummary:
        summary = ConversationSummary(
            thread_id=thread_id,
            from_turn_index=from_turn_index,
            to_turn_index=to_turn_index,
            summary_json=summary_json,
            summarizer_version=summarizer_version,
            quality_score=quality_score,
        )
        self.db.add(summary)
        await self.db.flush()
        await self.db.refresh(summary)
        return summary

    async def get_latest_summary(self, thread_id: UUID) -> Optional[ConversationSummary]:
        result = await self.db.execute(
            select(ConversationSummary)
            .where(ConversationSummary.thread_id == thread_id)
            .order_by(
                ConversationSummary.to_turn_index.desc(),
                ConversationSummary.created_at.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
