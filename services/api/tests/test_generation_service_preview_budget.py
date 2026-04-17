from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://sovrn:devpassword@localhost:5432/sovrn")

from app.services.generation import GenerationService  # noqa: E402
from app.core.config import settings  # noqa: E402


class _DelayedEngine:
    def __init__(self, delay_seconds: float, result: dict):
        self._delay_seconds = delay_seconds
        self._result = result

    async def generate(self, prompt: str) -> dict:
        _ = prompt
        await asyncio.sleep(self._delay_seconds)
        return self._result


@pytest.mark.asyncio
async def test_generate_code_enforces_preview_build_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GenerationService(db=None)
    project = SimpleNamespace(id="project-timeout", brief="brief", locale="en")

    async def _fake_get_engine() -> _DelayedEngine:
        return _DelayedEngine(
            delay_seconds=0.01,
            result={"files": {"index.html": "ok"}, "success": True, "generation_time_ms": 12},
        )

    monkeypatch.setattr(service, "_get_advanced_engine", _fake_get_engine)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_TIMEOUT_SECONDS", 0.001)

    result = await service.generate_code(project, {"brief": "Generate site"})

    assert result["status"] == "completed_fallback"
    assert result["fallback_reason"] == "timeout"
    assert "timed out" in result.get("error", "")
    assert "index.html" in result["files"]
    assert isinstance(result["preview_html"], str) and result["preview_html"].strip()
    assert result["build_budget"]["timeout_seconds"] == 0.001


@pytest.mark.asyncio
async def test_generate_code_applies_preview_file_budgets(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GenerationService(db=None)
    project = SimpleNamespace(id="project-budget", brief="brief", locale="en")

    async def _fake_get_engine() -> _DelayedEngine:
        return _DelayedEngine(
            delay_seconds=0,
            result={
                "files": {
                    "index.html": "abcdefghij",
                    "styles.css": "1234567890",
                    "script.js": "zzzz",
                },
                "success": True,
                "generation_time_ms": 25,
                "preview_html": "<html><body>this preview html should be trimmed by budget</body></html>",
                "design_style": "modern",
            },
        )

    monkeypatch.setattr(service, "_get_advanced_engine", _fake_get_engine)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_TIMEOUT_SECONDS", 5)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_MAX_FILES", 2)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_MAX_TOTAL_BYTES", 10)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_MAX_FILE_BYTES", 6)

    result = await service.generate_code(project, {"brief": "Generate site"})

    assert result["status"] == "completed"
    assert len(result["files"]) <= 2
    total_bytes = sum(len(content.encode("utf-8")) for content in result["files"].values())
    assert total_bytes <= 10
    assert all(len(content.encode("utf-8")) <= 6 for content in result["files"].values())

    budget = result["build_budget"]
    assert budget["max_files"] == 2
    assert budget["max_total_bytes"] == 10
    assert budget["max_file_bytes"] == 6
    assert budget["total_bytes"] <= 10
    assert budget["truncated_files"] >= 1
    assert budget["dropped_files"] >= 1


@pytest.mark.asyncio
async def test_generate_code_uses_cached_starter_template_when_generation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GenerationService(db=None)
    project = SimpleNamespace(id="project-fallback", brief="brief", locale="en")

    async def _fake_get_engine() -> _DelayedEngine:
        return _DelayedEngine(
            delay_seconds=0,
            result={
                "files": {},
                "success": False,
                "generation_time_ms": 8,
                "preview_html": "",
                "design_style": "minimal",
            },
        )

    monkeypatch.setattr(service, "_get_advanced_engine", _fake_get_engine)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_TIMEOUT_SECONDS", 5)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_MAX_FILES", 12)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_MAX_TOTAL_BYTES", 786432)
    monkeypatch.setattr(settings, "PREVIEW_BUILD_MAX_FILE_BYTES", 262144)

    result = await service.generate_code(project, {"brief": "Generate site", "style": "minimal"})

    assert result["status"] == "completed_fallback"
    assert result["fallback_reason"] == "generation_failed"
    assert result["design_style"] == "minimal"
    assert "index.html" in result["files"]
    assert isinstance(result["preview_html"], str) and result["preview_html"].strip()
