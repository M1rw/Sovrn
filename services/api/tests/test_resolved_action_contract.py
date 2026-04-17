from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.responses import JSONResponse


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://sovrn:devpassword@localhost:5432/sovrn")

from app.api.v1.endpoints import ai  # noqa: E402


def _request(user_message: str) -> ai.ChatRequest:
    return ai.ChatRequest(
        messages=[ai.ChatMessage(role="user", content=user_message)],
    )


def _structured_content(
    *,
    action: str,
    assistant_message: str = "ok",
    generation_request: dict | None = None,
    revision_request: dict | None = None,
) -> str:
    payload = {
        "version": "1.0",
        "action": action,
        "assistant_message": assistant_message,
        "questions": [],
        "generation_request": generation_request,
        "revision_request": revision_request,
        "state_patch": {},
        "meta": {"source": "unit_test"},
    }
    return json.dumps(payload)


@pytest.mark.parametrize("action", ["respond", "ask_clarification", "error_recoverable"])
def test_resolved_action_accepts_base_actions(action: str) -> None:
    metadata = ai._resolve_backend_action_metadata(
        _request("hello there"),
        _structured_content(action=action),
    )
    assert metadata["resolved_action"] == action
    assert metadata["resolved_action_reason"] == "accepted"


def test_ready_to_generate_passes_with_site_intent_and_brief() -> None:
    metadata = ai._resolve_backend_action_metadata(
        _request("please build a website for my coffee shop"),
        _structured_content(
            action="ready_to_generate",
            generation_request={"brief": "Modern coffee shop website with menu and contact."},
        ),
    )
    assert metadata["resolved_action"] == "ready_to_generate"
    assert metadata["resolved_action_reason"] == "generation_gate_passed"
    assert metadata["generation_handoff_allowed"] is True


def test_ready_to_generate_falls_back_when_brief_missing() -> None:
    metadata = ai._resolve_backend_action_metadata(
        _request("please build a website for my coffee shop"),
        _structured_content(
            action="ready_to_generate",
            generation_request={"brief": "   "},
        ),
    )
    assert metadata["resolved_action"] == "ask_clarification"
    assert metadata["resolved_action_reason"] == "generation_gate_failed"


def test_propose_revision_passes_with_revision_intent_and_scope() -> None:
    metadata = ai._resolve_backend_action_metadata(
        _request("please revise the layout and update the hero section"),
        _structured_content(
            action="propose_revision",
            revision_request={
                "change_summary": "Adjust spacing and hero hierarchy",
                "targets": ["hero", "pricing"],
            },
        ),
    )
    assert metadata["resolved_action"] == "propose_revision"
    assert metadata["resolved_action_reason"] == "revision_gate_passed"


def test_propose_revision_falls_back_without_revision_scope() -> None:
    metadata = ai._resolve_backend_action_metadata(
        _request("please revise the layout"),
        _structured_content(
            action="propose_revision",
            revision_request={"change_summary": "", "targets": []},
        ),
    )
    assert metadata["resolved_action"] == "ask_clarification"
    assert metadata["resolved_action_reason"] == "revision_gate_failed"


def test_attach_metadata_includes_conversation_fields_even_when_phase5_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ai.settings, "AI_RESOLVED_ACTION_RESPONSE_ENABLED", False)

    request = _request("hello")
    base = ai.ChatResponse(
        content="fallback",
        provider="fallback",
        model="fallback-model",
        thinking=None,
        latency_ms=0,
        tokens_used=0,
        success=True,
    )

    response = ai._attach_phase5_response_metadata(
        request,
        base,
        model_content="",
        conversation_metadata={
            "thread_id": "11111111-1111-4111-8111-111111111111",
            "turn_index": 1,
            "state_version": 2,
            "idempotency_key": "idem-check",
        },
    )

    assert isinstance(response, JSONResponse)
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["thread_id"] == "11111111-1111-4111-8111-111111111111"
    assert payload["turn_index"] == 1
    assert "resolved_action" not in payload
