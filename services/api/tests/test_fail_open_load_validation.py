from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.responses import JSONResponse


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://sovrn:devpassword@localhost:5432/sovrn")

from app.api.v1.endpoints import ai  # noqa: E402
from app.lib.ai.providers import AIProvider, AIResponse  # noqa: E402


class _LoadFakeEngine:
    def __init__(self, content: str):
        self._content = content

    async def generate(self, **kwargs) -> AIResponse:
        _ = kwargs
        return AIResponse(
            content=self._content,
            provider=AIProvider.PHI3_LOCAL,
            model="mock-load-engine",
            latency_ms=7,
            tokens_used=20,
            success=True,
        )


def _chat_request(user_id: UUID, idx: int) -> ai.ChatRequest:
    return ai.ChatRequest(
        messages=[
            ai.ChatMessage(
                role="user",
                content=f"Create website draft request {idx}",
            )
        ],
        user_id=user_id,
        idempotency_key=f"load-idem-{idx:04d}",
        json_mode=True,
    )


def _structured_response_payload() -> str:
    return (
        '{"version":"1.0","action":"respond","assistant_message":"ok","questions":[],'
        '"generation_request":null,"revision_request":null,"state_patch":{},"meta":{"source":"load"}}'
    )


@pytest.mark.asyncio
async def test_summary_contract_rejection_path_under_load(monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = Path(__file__).resolve().parent / "test_conversation_persistence_integration.py"
    spec = importlib.util.spec_from_file_location("conversation_persistence_harness", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load test harness module from {module_path}")
    harness_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = harness_module
    spec.loader.exec_module(harness_module)

    _build_ai_response = harness_module._build_ai_response
    _build_chat_request = harness_module._build_chat_request
    _install_persistence_harness = harness_module._install_persistence_harness

    iterations = 80
    store, db = _install_persistence_harness(
        monkeypatch,
        summarization_enabled=True,
        summary_trigger_turns=1,
    )

    monkeypatch.setattr(
        ai,
        "parse_conversation_summary_output",
        lambda _payload: SimpleNamespace(success=False, parsed=None, error="invalid-summary"),
    )

    response = _build_ai_response("load-summary-rejection")

    success_count = 0
    for idx in range(iterations):
        request = _build_chat_request(
            user_id=uuid4(),
            idempotency_key=f"summary-load-{idx:04d}",
        )
        metadata = await ai._persist_conversation_shadow_state(request, response)
        if metadata is not None:
            success_count += 1

    assert success_count == iterations
    assert store.summary_writes == 0
    assert db.commits == iterations


@pytest.mark.asyncio
async def test_parser_fail_open_behavior_under_load(monkeypatch: pytest.MonkeyPatch) -> None:
    iterations = 60

    async def _fake_get_ai_engine() -> _LoadFakeEngine:
        return _LoadFakeEngine(_structured_response_payload())

    async def _noop_persist(*args, **kwargs):
        _ = args, kwargs
        return None

    async def _passthrough_compaction(request: ai.ChatRequest):
        return list(request.messages)

    monkeypatch.setattr(ai.settings, "AI_STRUCTURED_SHADOW_ENABLED", True)
    monkeypatch.setattr(ai.settings, "AI_RESOLVED_ACTION_RESPONSE_ENABLED", True)
    monkeypatch.setattr(ai.settings, "AI_STATE_PERSIST_ENABLED", False)
    monkeypatch.setattr(ai, "get_ai_engine", _fake_get_ai_engine)
    monkeypatch.setattr(ai, "_persist_conversation_shadow_state", _noop_persist)
    monkeypatch.setattr(ai, "_resolve_compacted_messages", _passthrough_compaction)
    monkeypatch.setattr(
        ai,
        "parse_structured_model_output",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("forced-parser-failure")),
    )

    responses = []
    for idx in range(iterations):
        request = _chat_request(uuid4(), idx)
        response = await ai.chat_completion(request)
        responses.append(response)

    assert len(responses) == iterations
    for response in responses:
        if isinstance(response, ai.ChatResponse):
            assert response.success is True
        else:
            assert isinstance(response, JSONResponse)
            body = json.loads(response.body.decode("utf-8"))
            assert body["success"] is True
