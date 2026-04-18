from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://sovrn:devpassword@localhost:5432/sovrn")

from app.api.v1.endpoints import projects  # noqa: E402
from app.schemas import PatchContractRequest  # noqa: E402


def _build_valid_contract_payload(*, project_id: str | None = None) -> dict[str, object]:
    return {
        "version": "1.0",
        "project_id": project_id,
        "fallback_mode": "safe_rewrite",
        "operations": [
            {
                "op": "replace_file",
                "path": "src/app/page.tsx",
                "language": "tsx",
                "content": "export default function Page() { return null; }\n",
            },
            {
                "op": "replace_range",
                "path": "src/styles/global.css",
                "language": "css",
                "range": {
                    "start": 0,
                    "end": 22,
                },
                "content": "body{margin:0;}\n",
            },
        ],
    }


def test_patch_contract_accepts_valid_payload() -> None:
    payload = _build_valid_contract_payload(
        project_id="00000000-0000-0000-0000-000000000111"
    )

    contract = PatchContractRequest.model_validate(payload)

    assert contract.version == "1.0"
    assert contract.fallback_mode == "safe_rewrite"
    assert len(contract.operations) == 2
    assert contract.operations[0].path == "src/app/page.tsx"
    assert contract.operations[1].range is not None
    assert contract.operations[1].range.start == 0


def test_patch_contract_rejects_path_traversal() -> None:
    payload = _build_valid_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "../secrets.env",
            "content": "x",
        }
    ]

    with pytest.raises(ValidationError) as exc:
        PatchContractRequest.model_validate(payload)

    assert "traversal" in str(exc.value).lower()


def test_patch_contract_rejects_replace_range_without_range() -> None:
    payload = _build_valid_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_range",
            "path": "src/app/page.tsx",
            "content": "noop",
        }
    ]

    with pytest.raises(ValidationError) as exc:
        PatchContractRequest.model_validate(payload)

    assert "replace_range requires range" in str(exc.value)


def test_patch_contract_rejects_duplicate_targets() -> None:
    payload = _build_valid_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "src/app/page.tsx",
            "content": "a",
        },
        {
            "op": "replace_file",
            "path": "src/app/page.tsx",
            "content": "b",
        },
    ]

    with pytest.raises(ValidationError) as exc:
        PatchContractRequest.model_validate(payload)

    assert "duplicate patch operation target" in str(exc.value).lower()


def test_patch_contract_rejects_unknown_fields() -> None:
    payload = _build_valid_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "src/app/page.tsx",
            "content": "x",
            "unexpected": True,
        }
    ]

    with pytest.raises(ValidationError) as exc:
        PatchContractRequest.model_validate(payload)

    assert "extra inputs are not permitted" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_patch_contract_endpoint_returns_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = UUID("00000000-0000-0000-0000-000000000111")

    async def _fake_get_project_for_user(*, project_id: UUID, user_id: UUID, db):
        _ = db
        assert project_id == UUID("00000000-0000-0000-0000-000000000111")
        assert user_id == UUID("00000000-0000-0000-0000-000000000999")
        return SimpleNamespace(id=project_id)

    monkeypatch.setattr(projects, "_get_project_for_user", _fake_get_project_for_user)

    request = PatchContractRequest.model_validate(
        _build_valid_contract_payload(project_id=str(project_id))
    )

    response = await projects.validate_patch_contract(
        project_id=project_id,
        request=request,
        user=SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000999")),
        db=None,
    )

    assert response.valid is True
    assert response.project_id == project_id
    assert response.operation_count == 2
    assert response.files_touched == ["src/app/page.tsx", "src/styles/global.css"]


@pytest.mark.asyncio
async def test_validate_patch_contract_endpoint_rejects_project_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = UUID("00000000-0000-0000-0000-000000000111")

    async def _fake_get_project_for_user(*, project_id: UUID, user_id: UUID, db):
        _ = user_id
        _ = db
        return SimpleNamespace(id=project_id)

    monkeypatch.setattr(projects, "_get_project_for_user", _fake_get_project_for_user)

    request = PatchContractRequest.model_validate(
        _build_valid_contract_payload(
            project_id="00000000-0000-0000-0000-000000000222"
        )
    )

    with pytest.raises(HTTPException) as mismatch:
        await projects.validate_patch_contract(
            project_id=project_id,
            request=request,
            user=SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000999")),
            db=None,
        )

    assert mismatch.value.status_code == 400
    assert "project_id" in mismatch.value.detail
