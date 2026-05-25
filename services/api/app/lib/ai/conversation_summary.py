"""Conversation summary trigger and contract helpers.

P4-1 scope only:
- deterministic trigger decision logic
- strict non-authoritative summary output contract validation
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class ConversationSummaryOutput(BaseModel):
    """Non-authoritative summary output contract."""

    version: str = "1.0"
    non_authoritative: Literal[True] = True
    from_turn_index: int = Field(ge=1)
    to_turn_index: int = Field(ge=1)
    summary: str = Field(min_length=1, max_length=4000)
    key_points: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_turn_range(self) -> "ConversationSummaryOutput":
        if self.to_turn_index < self.from_turn_index:
            raise ValueError("to_turn_index must be greater than or equal to from_turn_index")
        return self


@dataclass(frozen=True)
class ConversationSummaryParseResult:
    """Safe parse result for summary contract validation."""

    success: bool
    parsed: Optional[ConversationSummaryOutput] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class SummaryTriggerDecision:
    """Deterministic decision for when to persist a summary window."""

    should_trigger: bool
    from_turn_index: Optional[int] = None
    to_turn_index: Optional[int] = None
    reason: str = ""


def should_trigger_conversation_summary(
    *,
    current_turn_index: int,
    latest_summary_to_turn_index: Optional[int],
    trigger_every_turns: int,
) -> SummaryTriggerDecision:
    """Decide if summarization should run using deterministic turn windows."""
    if trigger_every_turns < 1:
        raise ValueError("trigger_every_turns must be >= 1")

    if current_turn_index < 1:
        return SummaryTriggerDecision(False, reason="invalid_turn_index")

    latest_covered = latest_summary_to_turn_index if latest_summary_to_turn_index is not None else 0
    if latest_covered >= current_turn_index:
        return SummaryTriggerDecision(False, reason="already_covered")

    unsummarized_turns = current_turn_index - latest_covered
    if unsummarized_turns < trigger_every_turns:
        return SummaryTriggerDecision(False, reason="window_too_small")

    if unsummarized_turns % trigger_every_turns != 0:
        return SummaryTriggerDecision(False, reason="interval_not_reached")

    return SummaryTriggerDecision(
        True,
        from_turn_index=latest_covered + 1,
        to_turn_index=current_turn_index,
        reason="triggered",
    )


def parse_conversation_summary_output(payload: Any) -> ConversationSummaryParseResult:
    """Validate summary payload safely without raising."""
    try:
        candidate: Any = payload
        if isinstance(payload, str):
            candidate = json.loads(payload)

        if not isinstance(candidate, dict):
            return ConversationSummaryParseResult(
                success=False,
                error="summary payload must be a JSON object",
            )

        parsed = ConversationSummaryOutput.model_validate(candidate)
        return ConversationSummaryParseResult(success=True, parsed=parsed)
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return ConversationSummaryParseResult(success=False, error=str(exc))
