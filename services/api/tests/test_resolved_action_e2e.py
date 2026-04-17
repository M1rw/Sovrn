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
from app.lib.ai.providers import AIProvider, AIResponse  # noqa: E402


class _FakeEngine:
    def __init__(self, content: str):
        self._content = content

    async def generate(self, **kwargs) -> AIResponse:
        _ = kwargs
        return AIResponse(
            content=self._content,
            provider=AIProvider.PHI3_LOCAL,
            model="mock-phi3",
            latency_ms=9,
            tokens_used=18,
            success=True,
        )


def _request(message: str) -> ai.ChatRequest:
    return ai.ChatRequest(
        messages=[ai.ChatMessage(role="user", content=message)],
        provider="auto",
        mode="balanced",
        json_mode=True,
    )


def _structured_payload(
    *,
    action: str,
    assistant_message: str,
    generation_request: dict | None = None,
    revision_request: dict | None = None,
) -> str:
    return json.dumps(
        {
            "version": "1.0",
            "action": action,
            "assistant_message": assistant_message,
            "questions": [],
            "generation_request": generation_request,
            "revision_request": revision_request,
            "state_patch": {},
            "meta": {"source": "unit_test_e2e"},
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_message,model_content,expected_action,expected_handoff",
    [
        (
            "hello assistant",
            _structured_payload(
                action="respond",
                assistant_message="Hello back.",
            ),
            "respond",
            False,
        ),
        (
            "can you clarify what information you need?",
            _structured_payload(
                action="ask_clarification",
                assistant_message="I need your target audience and pages.",
            ),
            "ask_clarification",
            False,
        ),
        (
            "build a website for my coffee shop",
            _structured_payload(
                action="ready_to_generate",
                assistant_message="Ready to generate now.",
                generation_request={"brief": "Modern coffee shop site with menu and contact."},
            ),
            "ready_to_generate",
            True,
        ),
        (
            "please revise the hero and pricing sections",
            _structured_payload(
                action="propose_revision",
                assistant_message="I can apply those revisions.",
                revision_request={
                    "change_summary": "Refine hero hierarchy and pricing emphasis.",
                    "targets": ["hero", "pricing"],
                },
            ),
            "propose_revision",
            False,
        ),
    ],
)
async def test_chat_completion_end_to_end_resolved_action_outcomes(
    monkeypatch: pytest.MonkeyPatch,
    user_message: str,
    model_content: str,
    expected_action: str,
    expected_handoff: bool,
) -> None:
    async def _fake_get_ai_engine() -> _FakeEngine:
        return _FakeEngine(model_content)

    async def _noop_persist(*args, **kwargs):
        _ = args, kwargs
        return None

    async def _passthrough_compaction(request: ai.ChatRequest):
        return list(request.messages)

    monkeypatch.setattr(ai.settings, "AI_RESOLVED_ACTION_RESPONSE_ENABLED", True)
    monkeypatch.setattr(ai.settings, "AI_STATE_PERSIST_ENABLED", False)
    monkeypatch.setattr(ai, "get_ai_engine", _fake_get_ai_engine)
    monkeypatch.setattr(ai, "_persist_conversation_shadow_state", _noop_persist)
    monkeypatch.setattr(ai, "_resolve_compacted_messages", _passthrough_compaction)

    response = await ai.chat_completion(_request(user_message))

    assert isinstance(response, JSONResponse)
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["success"] is True
    assert payload["resolved_action"] == expected_action
    assert payload["generation_handoff_allowed"] is expected_handoff
    assert payload["generation_handoff_initiated"] is False
