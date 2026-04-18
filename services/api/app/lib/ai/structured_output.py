"""Structured model-output contract parser for shadow-mode validation.

This module validates model output against a strict contract and performs at
most one repair attempt using safe JSON extraction heuristics.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ValidationError


class StructuredModelOutput(BaseModel):
    """Contract for proposed structured model output in shadow mode."""

    version: str = "1.0"
    action: Literal[
        "respond",
        "ask_clarification",
        "ready_to_generate",
        "propose_revision",
        "error_recoverable",
    ]
    assistant_message: str = Field(min_length=1)
    questions: list[str] = Field(default_factory=list)
    generation_request: Optional[dict[str, Any]] = None
    revision_request: Optional[dict[str, Any]] = None
    state_patch: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any]


@dataclass(frozen=True)
class StructuredOutputParseResult:
    """Result of structured output parse and optional repair."""

    success: bool
    parsed: Optional[StructuredModelOutput] = None
    error: Optional[str] = None
    repaired: bool = False
    repair_attempts: int = 0


_PARSE_EXCEPTIONS = (json.JSONDecodeError, ValidationError, TypeError, ValueError)


def parse_structured_model_output(content: str, max_repair_attempts: int = 1) -> StructuredOutputParseResult:
    """Parse structured model output with at most one repair attempt."""
    text = (content or "").strip()
    if not text:
        return StructuredOutputParseResult(
            success=False,
            error="Empty model output cannot be parsed as structured JSON.",
            repaired=False,
            repair_attempts=0,
        )

    direct_error: Optional[str] = None
    try:
        parsed = _parse_candidate(text)
        return StructuredOutputParseResult(success=True, parsed=parsed, repaired=False, repair_attempts=0)
    except _PARSE_EXCEPTIONS as e:
        direct_error = str(e)

    if max_repair_attempts <= 0:
        return StructuredOutputParseResult(
            success=False,
            error=f"Direct parse failed: {direct_error}",
            repaired=False,
            repair_attempts=0,
        )

    repair_attempts = 1
    repaired_candidate = _extract_repair_candidate(text)
    if not repaired_candidate:
        return StructuredOutputParseResult(
            success=False,
            error=f"Direct parse failed and no repair candidate found: {direct_error}",
            repaired=True,
            repair_attempts=repair_attempts,
        )

    try:
        parsed = _parse_candidate(repaired_candidate)
        return StructuredOutputParseResult(
            success=True,
            parsed=parsed,
            repaired=True,
            repair_attempts=repair_attempts,
        )
    except _PARSE_EXCEPTIONS as e:
        return StructuredOutputParseResult(
            success=False,
            error=f"Direct parse failed ({direct_error}); repair parse failed ({e})",
            repaired=True,
            repair_attempts=repair_attempts,
        )


def _parse_candidate(candidate: str) -> StructuredModelOutput:
    payload = json.loads(candidate)
    return StructuredModelOutput.model_validate(payload)


def _extract_repair_candidate(text: str) -> Optional[str]:
    json_block_match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if json_block_match:
        return json_block_match.group(1).strip()

    code_block_match = re.search(r"```\s*(.*?)\s*```", text, flags=re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    return None
