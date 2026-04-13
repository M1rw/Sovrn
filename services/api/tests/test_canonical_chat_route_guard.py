from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_canonical_chat_governance.py"


_spec = importlib.util.spec_from_file_location("canonical_chat_guard", SCRIPT_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load governance script from {SCRIPT_PATH}")

_guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_guard)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class CanonicalChatRouteGuardTests(unittest.TestCase):
    def test_governance_check_passes_in_current_repo(self) -> None:
        errors = _guard.run_governance_check(REPO_ROOT)
        self.assertEqual(errors, [])

    def test_governance_check_rejects_unknown_absolute_chat_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            _write(
                temp_root / "services/api/app/api/v1/endpoints/ai.py",
                "@router.post(\"/chat\")\nasync def chat_completion():\n    return {}\n",
            )
            _write(
                temp_root / "services/api/app/api/v1/router.py",
                'api_router.include_router(ai.router, prefix="/ai", tags=["AI"])\n',
            )
            _write(
                temp_root / "services/api/main.py",
                'app.include_router(api_router, prefix="/api/v1")\n',
            )
            _write(
                temp_root / "services/api/app/api/v1/endpoints/rogue.py",
                "@app.post(\"/api/v1/ai/chat\")\nasync def rogue_chat():\n    return {}\n",
            )

            errors = _guard.run_governance_check(temp_root)
            self.assertTrue(any("Unknown absolute chat route" in error for error in errors))

    def test_governance_check_rejects_noncanonical_relative_chat_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            _write(
                temp_root / "services/api/app/api/v1/endpoints/ai.py",
                "@router.post(\"/chat\")\nasync def chat_completion():\n    return {}\n",
            )
            _write(
                temp_root / "services/api/app/api/v1/router.py",
                'api_router.include_router(ai.router, prefix="/ai", tags=["AI"])\n',
            )
            _write(
                temp_root / "services/api/main.py",
                'app.include_router(api_router, prefix="/api/v1")\n',
            )
            _write(
                temp_root / "services/api/app/api/v1/endpoints/extra.py",
                "@router.post(\"/chat\")\nasync def extra_chat():\n    return {}\n",
            )

            errors = _guard.run_governance_check(temp_root)
            self.assertTrue(any("Non-canonical /chat route" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
