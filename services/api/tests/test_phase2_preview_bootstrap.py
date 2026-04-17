from __future__ import annotations

import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://sovrn:devpassword@localhost:5432/sovrn")

from app.api.v1.endpoints import projects  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import create_access_token, create_preview_session_token, verify_token  # noqa: E402
from app.schemas import PreviewArtifactFile  # noqa: E402


class _SingleIterationRequest:
    def __init__(self) -> None:
        self._checks = 0

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._checks > 1


async def _collect_stream_frames(response, count: int) -> list[str]:
    frames: list[str] = []
    iterator = response.body_iterator
    try:
        for _ in range(count):
            chunk = await anext(iterator)
            if isinstance(chunk, (bytes, bytearray)):
                frames.append(chunk.decode("utf-8"))
            else:
                frames.append(str(chunk))
    finally:
        close = getattr(iterator, "aclose", None)
        if callable(close):
            await close()

    return frames


def _sse_payload_from_frame(frame: str) -> dict[str, object]:
    for line in frame.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: ") :])

    raise AssertionError("Expected SSE frame to include data payload")


def test_normalize_preview_artifact_files_filters_invalid_entries() -> None:
    normalized = projects._normalize_preview_artifact_files(
        [
            {
                "path": "index.html",
                "content": "<html><body>Hello</body></html>",
                "language": "html",
            },
            {
                "path": "assets/main.js",
                "content": "console.log('ok');",
                "language": "javascript",
            },
            {"path": "", "content": "invalid"},
            {"path": None, "content": "invalid"},
            "not-a-file",
        ]
    )

    assert len(normalized) == 2
    assert normalized[0].path == "index.html"
    assert normalized[0].language == "html"
    assert normalized[0].size_bytes == len("<html><body>Hello</body></html>".encode("utf-8"))
    assert normalized[1].path == "assets/main.js"
    assert normalized[1].language == "javascript"


def test_select_preview_html_prefers_requested_entrypoint() -> None:
    files = [
        PreviewArtifactFile(
            path="index.html",
            content="<html>root index</html>",
            language="html",
            size_bytes=23,
        ),
        PreviewArtifactFile(
            path="preview/custom.html",
            content="<html>custom preview</html>",
            language="html",
            size_bytes=27,
        ),
    ]

    selected = projects._select_preview_html(
        files=files,
        entrypoint="preview/custom.html",
        code_output={"preview_html": "<html>fallback preview</html>"},
    )

    assert selected == "<html>custom preview</html>"


def test_select_preview_html_falls_back_to_code_output() -> None:
    selected = projects._select_preview_html(
        files=[],
        entrypoint="index.html",
        code_output={"preview_html": "<html>from-code-output</html>"},
    )

    assert selected == "<html>from-code-output</html>"


def test_create_preview_session_token_includes_bootstrap_claims() -> None:
    token, expires_at = create_preview_session_token(
        subject="00000000-0000-0000-0000-000000000111",
        project_id="00000000-0000-0000-0000-000000000222",
        generation_id="00000000-0000-0000-0000-000000000333",
        entrypoint="index.html",
        expires_delta=timedelta(minutes=5),
    )

    verified = verify_token(token, token_type="preview_session")
    assert verified is not None
    assert verified.user_id == "00000000-0000-0000-0000-000000000111"
    assert verified.expires_at <= expires_at

    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    assert payload["project_id"] == "00000000-0000-0000-0000-000000000222"
    assert payload["generation_id"] == "00000000-0000-0000-0000-000000000333"
    assert payload["entrypoint"] == "index.html"
    assert payload["type"] == "preview_session"


def test_decode_preview_session_claims_rejects_access_token() -> None:
    access_token = create_access_token(subject="00000000-0000-0000-0000-000000000999")

    decoded = projects._decode_preview_session_claims(access_token)

    assert decoded is None


def test_resolve_preview_session_access_enforces_generation_and_entrypoint() -> None:
    token, _ = create_preview_session_token(
        subject="00000000-0000-0000-0000-000000000111",
        project_id="00000000-0000-0000-0000-000000000222",
        generation_id="00000000-0000-0000-0000-000000000333",
        entrypoint="index.html",
    )
    payload = projects._decode_preview_session_claims(token)
    assert payload is not None

    generation_id, entrypoint, _ = projects._resolve_preview_session_access(
        payload=payload,
        project_id=UUID("00000000-0000-0000-0000-000000000222"),
        generation_id=None,
        entrypoint="index.html",
    )
    assert generation_id == UUID("00000000-0000-0000-0000-000000000333")
    assert entrypoint == "index.html"

    with pytest.raises(HTTPException) as mismatch_generation:
        projects._resolve_preview_session_access(
            payload=payload,
            project_id=UUID("00000000-0000-0000-0000-000000000222"),
            generation_id=UUID("00000000-0000-0000-0000-000000000444"),
            entrypoint="index.html",
        )
    assert mismatch_generation.value.status_code == 403

    with pytest.raises(HTTPException) as mismatch_entrypoint:
        projects._resolve_preview_session_access(
            payload=payload,
            project_id=UUID("00000000-0000-0000-0000-000000000222"),
            generation_id=None,
            entrypoint="preview/custom.html",
        )
    assert mismatch_entrypoint.value.status_code == 403


def test_serialize_sse_event_formats_event_frame() -> None:
    frame = projects._serialize_sse_event(
        "preview.updated",
        {
            "project_id": "00000000-0000-0000-0000-000000000222",
            "generation_version": 3,
        },
    )

    assert frame.startswith("event: preview.updated\n")
    assert "data: {\"project_id\":\"00000000-0000-0000-0000-000000000222\",\"generation_version\":3}" in frame
    assert frame.endswith("\n\n")


@pytest.mark.asyncio
async def test_stream_preview_events_requires_authentication() -> None:
    with pytest.raises(HTTPException) as auth_required:
        await projects.stream_preview_events(
            project_id=UUID("00000000-0000-0000-0000-000000000222"),
            request=_SingleIterationRequest(),
            generation_id=None,
            entrypoint="index.html",
            preview_token=None,
            poll_interval_ms=250,
            user=None,
            credentials=None,
            db=None,
        )

    assert auth_required.value.status_code == 401
    assert auth_required.value.detail == "Authentication required"


@pytest.mark.asyncio
async def test_stream_preview_events_rejects_invalid_preview_token() -> None:
    with pytest.raises(HTTPException) as invalid_token:
        await projects.stream_preview_events(
            project_id=UUID("00000000-0000-0000-0000-000000000222"),
            request=_SingleIterationRequest(),
            generation_id=None,
            entrypoint="index.html",
            preview_token="invalid-preview-session-token",
            poll_interval_ms=250,
            user=None,
            credentials=None,
            db=None,
        )

    assert invalid_token.value.status_code == 401
    assert invalid_token.value.detail == "Invalid preview session token"


@pytest.mark.asyncio
async def test_stream_preview_events_emits_update_and_heartbeat_for_preview_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = UUID("00000000-0000-0000-0000-000000000222")
    generation_id = UUID("00000000-0000-0000-0000-000000000333")
    preview_token, _ = create_preview_session_token(
        subject="00000000-0000-0000-0000-000000000111",
        project_id=str(project_id),
        generation_id=str(generation_id),
        entrypoint="index.html",
        expires_delta=timedelta(minutes=5),
    )

    project = SimpleNamespace(id=project_id)
    generation = SimpleNamespace(
        id=generation_id,
        version=2,
        files=[
            {
                "path": "index.html",
                "content": "<html><body>Hello stream</body></html>",
                "language": "html",
            }
        ],
        code_output={"preview_html": "<html><body>fallback</body></html>"},
    )

    async def _fake_get_project(project_id: UUID, db):
        _ = db
        assert project_id == project.id
        return project

    async def _fake_get_preview_generation(project_id: UUID, db, generation_id: UUID | None = None):
        _ = db
        assert project_id == project.id
        assert generation_id in (None, generation.id)
        return generation

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(projects, "_get_project", _fake_get_project)
    monkeypatch.setattr(projects, "_get_preview_generation", _fake_get_preview_generation)
    monkeypatch.setattr(projects.asyncio, "sleep", _no_sleep)

    response = await projects.stream_preview_events(
        project_id=project_id,
        request=_SingleIterationRequest(),
        generation_id=generation_id,
        entrypoint="index.html",
        preview_token=preview_token,
        poll_interval_ms=250,
        user=None,
        credentials=None,
        db=None,
    )

    frames = await _collect_stream_frames(response, count=3)
    assert frames[0].startswith("retry: 2000")
    assert frames[1].startswith("event: preview.updated")
    assert frames[2].startswith("event: heartbeat")

    update_payload = _sse_payload_from_frame(frames[1])
    assert update_payload["project_id"] == str(project_id)
    assert update_payload["generation_id"] == str(generation_id)
    assert update_payload["generation_version"] == 2
    assert update_payload["entrypoint"] == "index.html"
    assert update_payload["preview_html"] == "<html><body>Hello stream</body></html>"
    assert isinstance(update_payload["files"], list)
    assert update_payload["files"]
    assert update_payload["files"][0]["path"] == "index.html"
    assert update_payload["artifact_endpoint"] == (
        f"/api/v1/projects/{project_id}/preview-artifact?generation_id={generation_id}&entrypoint=index.html"
    )

    heartbeat_payload = _sse_payload_from_frame(frames[2])
    assert heartbeat_payload["project_id"] == str(project_id)
    assert heartbeat_payload["generation_id"] == str(generation_id)
    assert heartbeat_payload["generation_version"] == 2


@pytest.mark.asyncio
async def test_stream_preview_events_accepts_bearer_preview_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = UUID("00000000-0000-0000-0000-000000000222")
    generation_id = UUID("00000000-0000-0000-0000-000000000333")
    entrypoint = "preview/custom.html"
    preview_token, _ = create_preview_session_token(
        subject="00000000-0000-0000-0000-000000000111",
        project_id=str(project_id),
        generation_id=str(generation_id),
        entrypoint=entrypoint,
        expires_delta=timedelta(minutes=5),
    )

    project = SimpleNamespace(id=project_id)
    generation = SimpleNamespace(
        id=generation_id,
        version=4,
        files=[
            {
                "path": entrypoint,
                "content": "<html><body>Custom entrypoint</body></html>",
                "language": "html",
            }
        ],
        code_output={"preview_html": "<html><body>fallback</body></html>"},
    )

    async def _fake_get_project(project_id: UUID, db):
        _ = db
        assert project_id == project.id
        return project

    async def _fake_get_preview_generation(project_id: UUID, db, generation_id: UUID | None = None):
        _ = db
        assert project_id == project.id
        assert generation_id == generation.id
        return generation

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(projects, "_get_project", _fake_get_project)
    monkeypatch.setattr(projects, "_get_preview_generation", _fake_get_preview_generation)
    monkeypatch.setattr(projects.asyncio, "sleep", _no_sleep)

    response = await projects.stream_preview_events(
        project_id=project_id,
        request=_SingleIterationRequest(),
        generation_id=None,
        entrypoint=entrypoint,
        preview_token=None,
        poll_interval_ms=250,
        user=None,
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=preview_token),
        db=None,
    )

    frames = await _collect_stream_frames(response, count=2)
    assert frames[0].startswith("retry: 2000")
    assert frames[1].startswith("event: preview.updated")

    update_payload = _sse_payload_from_frame(frames[1])
    assert update_payload["generation_id"] == str(generation_id)
    assert update_payload["entrypoint"] == entrypoint
