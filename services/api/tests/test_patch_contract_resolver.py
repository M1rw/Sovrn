from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://sovrn:devpassword@localhost:5432/sovrn")

from app.api.v1.endpoints import projects  # noqa: E402
from app.schemas import PatchContractApplyRequest, PatchContractRequest  # noqa: E402
from app.services.patch_contract import resolve_patch_contract_files  # noqa: E402


def _build_contract_payload(*, fallback_mode: str = "safe_rewrite", project_id: str | None = None):
    return {
        "version": "1.0",
        "project_id": project_id,
        "fallback_mode": fallback_mode,
        "operations": [],
    }


def test_resolve_patch_contract_files_applies_replace_file_and_range() -> None:
    files = {
        "index.html": "<h1>Hello</h1>",
        "notes.txt": "0123456789",
    }

    payload = _build_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "index.html",
            "content": "<h1>Updated</h1>",
        },
        {
            "op": "replace_range",
            "path": "notes.txt",
            "range": {"start": 2, "end": 5},
            "content": "AB",
        },
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is True
    assert result.rolled_back is False
    assert result.applied_operations == 2
    assert result.conflicts == []
    assert result.files["index.html"] == "<h1>Updated</h1>"
    assert result.files["notes.txt"] == "01AB56789"


def test_resolve_patch_contract_files_formats_json_deterministically() -> None:
    files = {
        "config.json": "{}",
    }

    payload = _build_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "config.json",
            "language": "json",
            "content": '{"z":2,"a":1}',
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is True
    assert result.rolled_back is False
    assert result.files["config.json"] == "{\n  \"a\": 1,\n  \"z\": 2\n}\n"


def test_resolve_patch_contract_files_formats_css_with_normalized_whitespace() -> None:
    files = {
        "styles.css": "body{margin:0;}\n",
    }

    payload = _build_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "styles.css",
            "language": "css",
            "content": "body{margin:0;}  \r\n.main{color:red;}\t\r\n",
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is True
    assert result.rolled_back is False
    assert result.files["styles.css"] == "body{margin:0;}\n.main{color:red;}\n"


def test_resolve_patch_contract_files_rejects_invalid_json_range_transform() -> None:
    files = {
        "config.json": "{\"theme\": \"light\"}\n",
    }

    payload = _build_contract_payload(fallback_mode="reject")
    payload["operations"] = [
        {
            "op": "replace_range",
            "path": "config.json",
            "range": {"start": 10, "end": 17},
            "content": "light",
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is False
    assert result.rolled_back is True
    assert result.applied_operations == 0
    assert result.files == files
    assert len(result.conflicts) == 1
    assert result.conflicts[0].code == "invalid_range"
    assert "AST transformed parse failed" in result.conflicts[0].message


def test_resolve_patch_contract_files_safe_rewrite_fallback_on_invalid_json_range_transform() -> None:
    files = {
        "config.json": "{\"theme\": \"light\"}\n",
    }

    payload = _build_contract_payload(fallback_mode="safe_rewrite")
    payload["operations"] = [
        {
            "op": "replace_range",
            "path": "config.json",
            "range": {"start": 0, "end": 1},
            "content": "{\"theme\": \"dark\"}",
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is True
    assert result.rolled_back is False
    assert result.applied_operations == 1
    assert len(result.conflicts) == 1
    assert result.conflicts[0].code == "invalid_range"
    assert result.conflicts[0].fallback_applied is True
    assert result.files["config.json"] == "{\n  \"theme\": \"dark\"\n}\n"


def test_resolve_patch_contract_files_rejects_unbalanced_js_range_transform() -> None:
    files = {
        "main.js": "function run() { return 1; }\n",
    }
    end_offset = len(files["main.js"])

    payload = _build_contract_payload(fallback_mode="reject")
    payload["operations"] = [
        {
            "op": "replace_range",
            "path": "main.js",
            "range": {"start": 0, "end": end_offset},
            "content": "function run() { return 1;\n",
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is False
    assert result.rolled_back is True
    assert result.applied_operations == 0
    assert result.files == files
    assert len(result.conflicts) == 1
    assert result.conflicts[0].code == "invalid_range"
    assert "Unclosed delimiter" in result.conflicts[0].message


def test_resolve_patch_contract_files_safe_rewrite_for_unsupported_declared_language() -> None:
    files = {
        "index.html": "<main><h1>Hello</h1></main>\n",
    }

    payload = _build_contract_payload(fallback_mode="safe_rewrite")
    payload["operations"] = [
        {
            "op": "replace_range",
            "path": "index.html",
            "language": "html",
            "range": {"start": 10, "end": 15},
            "content": "Hi",
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is True
    assert result.rolled_back is False
    assert result.applied_operations == 1
    assert len(result.conflicts) == 1
    assert result.conflicts[0].code == "invalid_range"
    assert result.conflicts[0].fallback_applied is True
    assert "AST profile unsupported" in result.conflicts[0].message
    assert result.files["index.html"] == "<main><h1>Hi</h1></main>\n"


def test_resolve_patch_contract_files_rejects_unsupported_declared_language_without_fallback() -> None:
    files = {
        "index.html": "<main><h1>Hello</h1></main>\n",
    }

    payload = _build_contract_payload(fallback_mode="reject")
    payload["operations"] = [
        {
            "op": "replace_range",
            "path": "index.html",
            "language": "html",
            "range": {"start": 10, "end": 15},
            "content": "Hi",
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is False
    assert result.rolled_back is True
    assert result.applied_operations == 0
    assert result.files == files
    assert len(result.conflicts) == 1
    assert result.conflicts[0].code == "invalid_range"
    assert result.conflicts[0].fallback_applied is False
    assert "AST profile unsupported" in result.conflicts[0].message


def test_resolve_patch_contract_files_matches_deterministic_golden_snapshot() -> None:
    files = {
        "config.json": "{}\n",
        "styles.css": "body{margin:0;}\n",
        "src/main.ts": "export const answer = 0;\n",
    }
    margin_index = files["styles.css"].index("0")

    payload = _build_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "config.json",
            "language": "json",
            "content": '{"z":2,"a":{"k":1}}',
        },
        {
            "op": "replace_range",
            "path": "styles.css",
            "language": "css",
            "range": {"start": margin_index, "end": margin_index + 1},
            "content": "8",
        },
        {
            "op": "replace_file",
            "path": "src/main.ts",
            "language": "ts",
            "content": "export const answer = 42;   \r\n",
        },
    ]

    contract = PatchContractRequest.model_validate(payload)
    result_one = resolve_patch_contract_files(files, contract)
    result_two = resolve_patch_contract_files(files, contract)

    expected_files = {
        "config.json": "{\n  \"a\": {\n    \"k\": 1\n  },\n  \"z\": 2\n}\n",
        "styles.css": "body{margin:8;}\n",
        "src/main.ts": "export const answer = 42;\n",
    }

    assert result_one.applied is True
    assert result_one.rolled_back is False
    assert result_one.conflicts == []
    assert result_one.files == expected_files

    assert result_two.applied is True
    assert result_two.rolled_back is False
    assert result_two.conflicts == []
    assert result_two.files == expected_files
    assert result_two.files == result_one.files


def test_resolve_patch_contract_files_is_idempotent_on_reapply() -> None:
    files = {
        "config.json": "{}\n",
        "styles.css": "body{margin:0;}\n",
        "src/main.js": "export const ready = false;\n",
    }

    payload = _build_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "config.json",
            "language": "json",
            "content": '{"b":2,"a":1}',
        },
        {
            "op": "replace_file",
            "path": "styles.css",
            "language": "css",
            "content": "body{margin:0;}  \r\n",
        },
        {
            "op": "replace_file",
            "path": "src/main.js",
            "language": "js",
            "content": "export const ready = true;   \n",
        },
    ]

    contract = PatchContractRequest.model_validate(payload)
    first_pass = resolve_patch_contract_files(files, contract)
    second_pass = resolve_patch_contract_files(first_pass.files, contract)

    assert first_pass.applied is True
    assert first_pass.rolled_back is False
    assert first_pass.conflicts == []

    assert second_pass.applied is True
    assert second_pass.rolled_back is False
    assert second_pass.conflicts == []
    assert second_pass.files == first_pass.files


def _build_representative_regression_cases() -> list[
    tuple[str, dict[str, str], list[dict[str, object]], dict[str, str]]
]:
    marketing_files = {
        "index.html": "<main><h1>Launch</h1><button>Get Started</button></main>\n",
        "src/styles/global.css": ":root{--brand:#3366ff;}\n.hero{padding:24px;}\n",
        "src/content/home.json": '{"cta":"Get Started","sections":["hero","features"]}\n',
    }
    marketing_operations = [
        {
            "op": "replace_range",
            "path": "index.html",
            "range": {
                "start": marketing_files["index.html"].index("Get Started"),
                "end": marketing_files["index.html"].index("Get Started") + len("Get Started"),
            },
            "content": "Start Free Trial",
        },
        {
            "op": "replace_range",
            "path": "src/styles/global.css",
            "language": "css",
            "range": {
                "start": marketing_files["src/styles/global.css"].index("24"),
                "end": marketing_files["src/styles/global.css"].index("24") + 2,
            },
            "content": "32",
        },
        {
            "op": "replace_file",
            "path": "src/content/home.json",
            "language": "json",
            "content": '{"sections":["hero","features","proof"],"cta":"Start Free Trial"}',
        },
    ]
    marketing_expected = {
        "index.html": "<main><h1>Launch</h1><button>Start Free Trial</button></main>\n",
        "src/styles/global.css": ":root{--brand:#3366ff;}\n.hero{padding:32px;}\n",
        "src/content/home.json": "{\n  \"cta\": \"Start Free Trial\",\n  \"sections\": [\n    \"hero\",\n    \"features\",\n    \"proof\"\n  ]\n}\n",
    }

    dashboard_files = {
        "src/app/dashboard/page.tsx": "export default function Dashboard(){\n  return <main><h1>Overview</h1><p>Active users: 12</p></main>;\n}\n",
        "src/styles/dashboard.css": ".cards{display:grid;grid-template-columns:1fr 1fr;}\n",
        "src/config/dashboard.json": '{"refresh":30,"widgets":["sales","users"]}\n',
    }
    dashboard_operations = [
        {
            "op": "replace_range",
            "path": "src/app/dashboard/page.tsx",
            "language": "tsx",
            "range": {
                "start": dashboard_files["src/app/dashboard/page.tsx"].index("12"),
                "end": dashboard_files["src/app/dashboard/page.tsx"].index("12") + 2,
            },
            "content": "18",
        },
        {
            "op": "replace_file",
            "path": "src/styles/dashboard.css",
            "language": "css",
            "content": ".cards{display:grid;grid-template-columns:1fr 1fr 1fr;}   \r\n",
        },
        {
            "op": "replace_file",
            "path": "src/config/dashboard.json",
            "language": "json",
            "content": '{"widgets":["sales","users","alerts"],"refresh":15}',
        },
    ]
    dashboard_expected = {
        "src/app/dashboard/page.tsx": "export default function Dashboard(){\n  return <main><h1>Overview</h1><p>Active users: 18</p></main>;\n}\n",
        "src/styles/dashboard.css": ".cards{display:grid;grid-template-columns:1fr 1fr 1fr;}\n",
        "src/config/dashboard.json": "{\n  \"refresh\": 15,\n  \"widgets\": [\n    \"sales\",\n    \"users\",\n    \"alerts\"\n  ]\n}\n",
    }

    ecommerce_files = {
        "src/app/products/page.jsx": "export default function Products(){\n  return <section><h2>Catalog</h2><p>Items: 3</p></section>;\n}\n",
        "src/styles/catalog.css": ".grid{gap:12px;}\n",
        "src/data/catalog.json": '{"currency":"USD","items":[{"sku":"A1","price":10}]}\n',
    }
    ecommerce_operations = [
        {
            "op": "replace_range",
            "path": "src/app/products/page.jsx",
            "language": "jsx",
            "range": {
                "start": ecommerce_files["src/app/products/page.jsx"].index("3"),
                "end": ecommerce_files["src/app/products/page.jsx"].index("3") + 1,
            },
            "content": "4",
        },
        {
            "op": "replace_range",
            "path": "src/styles/catalog.css",
            "language": "css",
            "range": {
                "start": ecommerce_files["src/styles/catalog.css"].index("12"),
                "end": ecommerce_files["src/styles/catalog.css"].index("12") + 2,
            },
            "content": "16",
        },
        {
            "op": "replace_file",
            "path": "src/data/catalog.json",
            "language": "json",
            "content": '{"items":[{"sku":"A1","price":10},{"sku":"B2","price":25}],"currency":"USD"}',
        },
    ]
    ecommerce_expected = {
        "src/app/products/page.jsx": "export default function Products(){\n  return <section><h2>Catalog</h2><p>Items: 4</p></section>;\n}\n",
        "src/styles/catalog.css": ".grid{gap:16px;}\n",
        "src/data/catalog.json": "{\n  \"currency\": \"USD\",\n  \"items\": [\n    {\n      \"price\": 10,\n      \"sku\": \"A1\"\n    },\n    {\n      \"price\": 25,\n      \"sku\": \"B2\"\n    }\n  ]\n}\n",
    }

    return [
        ("marketing-landing", marketing_files, marketing_operations, marketing_expected),
        ("saas-dashboard", dashboard_files, dashboard_operations, dashboard_expected),
        ("ecommerce-catalog", ecommerce_files, ecommerce_operations, ecommerce_expected),
    ]


@pytest.mark.parametrize(
    ("scenario_name", "files", "operations", "expected_files"),
    _build_representative_regression_cases(),
)
def test_resolve_patch_contract_files_representative_project_regression(
    scenario_name: str,
    files: dict[str, str],
    operations: list[dict[str, object]],
    expected_files: dict[str, str],
) -> None:
    _ = scenario_name
    payload = _build_contract_payload()
    payload["operations"] = operations

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is True
    assert result.rolled_back is False
    assert result.conflicts == []
    assert result.applied_operations == len(operations)
    assert result.files == expected_files


def test_resolve_patch_contract_files_rolls_back_on_hash_mismatch() -> None:
    files = {
        "index.html": "<h1>Hello</h1>",
        "about.html": "<p>About</p>",
    }

    payload = _build_contract_payload()
    payload["operations"] = [
        {
            "op": "replace_file",
            "path": "index.html",
            "content": "<h1>New</h1>",
        },
        {
            "op": "replace_file",
            "path": "about.html",
            "expected_sha256": "0" * 64,
            "content": "<p>Updated</p>",
        },
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is False
    assert result.rolled_back is True
    assert result.applied_operations == 0
    assert result.files == files
    assert len(result.conflicts) == 1
    assert result.conflicts[0].code == "hash_mismatch"


def test_resolve_patch_contract_files_falls_back_to_rewrite_for_missing_range_file() -> None:
    payload = _build_contract_payload(fallback_mode="safe_rewrite")
    payload["operations"] = [
        {
            "op": "replace_range",
            "path": "src/new.ts",
            "range": {"start": 0, "end": 0},
            "content": "export const v = 1;\n",
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files({}, contract)

    assert result.applied is True
    assert result.rolled_back is False
    assert result.applied_operations == 1
    assert len(result.conflicts) == 1
    assert result.conflicts[0].code == "missing_file"
    assert result.conflicts[0].fallback_applied is True
    assert result.files["src/new.ts"] == "export const v = 1;\n"


def test_resolve_patch_contract_files_reject_mode_rolls_back_on_invalid_range() -> None:
    files = {"src/main.css": "body{}"}

    payload = _build_contract_payload(fallback_mode="reject")
    payload["operations"] = [
        {
            "op": "replace_range",
            "path": "src/main.css",
            "range": {"start": 0, "end": 50},
            "content": "body{margin:0}",
        }
    ]

    contract = PatchContractRequest.model_validate(payload)
    result = resolve_patch_contract_files(files, contract)

    assert result.applied is False
    assert result.rolled_back is True
    assert result.applied_operations == 0
    assert result.files == files
    assert len(result.conflicts) == 1
    assert result.conflicts[0].code == "invalid_range"
    assert result.conflicts[0].fallback_applied is False


@pytest.mark.asyncio
async def test_resolve_patch_contract_endpoint_returns_resolution_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = UUID("00000000-0000-0000-0000-000000000111")

    async def _fake_get_project_for_user(*, project_id: UUID, user_id: UUID, db):
        _ = db
        assert project_id == UUID("00000000-0000-0000-0000-000000000111")
        assert user_id == UUID("00000000-0000-0000-0000-000000000999")
        return SimpleNamespace(id=project_id)

    monkeypatch.setattr(projects, "_get_project_for_user", _fake_get_project_for_user)

    request = PatchContractApplyRequest.model_validate(
        {
            "contract": {
                "version": "1.0",
                "project_id": str(project_id),
                "fallback_mode": "safe_rewrite",
                "operations": [
                    {
                        "op": "replace_file",
                        "path": "index.html",
                        "content": "<h1>Resolved</h1>",
                    }
                ],
            },
            "files": {
                "index.html": "<h1>Old</h1>",
            },
        }
    )

    response = await projects.resolve_patch_contract(
        project_id=project_id,
        request=request,
        user=SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000999")),
        db=None,
    )

    assert response.applied is True
    assert response.rolled_back is False
    assert response.applied_operations == 1
    assert response.files["index.html"] == "<h1>Resolved</h1>"
    assert response.conflicts == []


@pytest.mark.asyncio
async def test_resolve_patch_contract_endpoint_rejects_project_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = UUID("00000000-0000-0000-0000-000000000111")

    async def _fake_get_project_for_user(*, project_id: UUID, user_id: UUID, db):
        _ = user_id
        _ = db
        return SimpleNamespace(id=project_id)

    monkeypatch.setattr(projects, "_get_project_for_user", _fake_get_project_for_user)

    request = PatchContractApplyRequest.model_validate(
        {
            "contract": {
                "version": "1.0",
                "project_id": "00000000-0000-0000-0000-000000000222",
                "fallback_mode": "safe_rewrite",
                "operations": [
                    {
                        "op": "replace_file",
                        "path": "index.html",
                        "content": "<h1>Resolved</h1>",
                    }
                ],
            },
            "files": {"index.html": "<h1>Old</h1>"},
        }
    )

    with pytest.raises(HTTPException) as mismatch:
        await projects.resolve_patch_contract(
            project_id=project_id,
            request=request,
            user=SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000999")),
            db=None,
        )

    assert mismatch.value.status_code == 400
    assert "project_id" in mismatch.value.detail
