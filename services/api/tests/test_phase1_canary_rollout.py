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


class _CanaryEngine:
    async def generate(self, **kwargs) -> AIResponse:
        _ = kwargs
        content = json.dumps(
            {
                "version": "1.0",
                "action": "respond",
                "assistant_message": "Canary ring response.",
                "questions": [],
                "generation_request": None,
                "revision_request": None,
                "state_patch": {},
                "meta": {"source": "canary"},
            }
        )
        return AIResponse(
            content=content,
            provider=AIProvider.PHI3_LOCAL,
            model="mock-canary",
            latency_ms=8,
            tokens_used=10,
            success=True,
        )


def _request() -> ai.ChatRequest:
    return ai.ChatRequest(
        messages=[ai.ChatMessage(role="user", content="Canary rollout request")],
        json_mode=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ring,flags",
    [
        (
            "5",
            {
                "AI_RESOLVED_ACTION_RESPONSE_ENABLED": False,
                "AI_STATE_PERSIST_ENABLED": False,
                "AI_CONTEXT_COMPACTION_ENABLED": False,
                "AI_STRUCTURED_SHADOW_ENABLED": False,
            },
        ),
        (
            "25",
            {
                "AI_RESOLVED_ACTION_RESPONSE_ENABLED": True,
                "AI_STATE_PERSIST_ENABLED": False,
                "AI_CONTEXT_COMPACTION_ENABLED": False,
                "AI_STRUCTURED_SHADOW_ENABLED": False,
            },
        ),
        (
            "50",
            {
                "AI_RESOLVED_ACTION_RESPONSE_ENABLED": True,
                "AI_STATE_PERSIST_ENABLED": True,
                "AI_CONTEXT_COMPACTION_ENABLED": False,
                "AI_STRUCTURED_SHADOW_ENABLED": True,
            },
        ),
        (
            "100",
            {
                "AI_RESOLVED_ACTION_RESPONSE_ENABLED": True,
                "AI_STATE_PERSIST_ENABLED": True,
                "AI_CONTEXT_COMPACTION_ENABLED": True,
                "AI_STRUCTURED_SHADOW_ENABLED": True,
            },
        ),
    ],
)
async def test_phase1_feature_flag_canary_rings(
    monkeypatch: pytest.MonkeyPatch,
    ring: str,
    flags: dict[str, bool],
) -> None:
    async def _fake_get_ai_engine() -> _CanaryEngine:
        return _CanaryEngine()

    async def _noop_persist(*args, **kwargs):
        _ = args, kwargs
        return None

    async def _passthrough_compaction(request: ai.ChatRequest):
        return list(request.messages)

    for key, value in flags.items():
        monkeypatch.setattr(ai.settings, key, value)

    monkeypatch.setattr(ai, "get_ai_engine", _fake_get_ai_engine)
    monkeypatch.setattr(ai, "_persist_conversation_shadow_state", _noop_persist)
    monkeypatch.setattr(ai, "_resolve_compacted_messages", _passthrough_compaction)

    response = await ai.chat_completion(_request())

    if flags["AI_RESOLVED_ACTION_RESPONSE_ENABLED"]:
        assert isinstance(response, JSONResponse), f"ring {ring} expected JSONResponse"
        payload = json.loads(response.body.decode("utf-8"))
        assert payload["success"] is True
        assert payload["resolved_action"] == "respond"
    else:
        assert isinstance(response, ai.ChatResponse), f"ring {ring} expected ChatResponse"
        assert response.success is True
