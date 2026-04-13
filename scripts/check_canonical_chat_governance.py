#!/usr/bin/env python3
"""Canonical chat route governance guard.

This script enforces one supported conversation path in the production stack while
allowing known legacy files to exist until deprecation tickets land.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

ROUTE_DECORATOR_RE = re.compile(
    r'^\s*@(?P<kind>app|router)\.post\(\s*["\'](?P<route>/api/v1/ai/chat|/chat)["\']',
    re.MULTILINE,
)

CANONICAL_CHAT_FILE = Path("services/api/app/api/v1/endpoints/ai.py")
ALLOWED_LEGACY_ABSOLUTE_FILES = {
    Path("services/api/simple_api.py"),
    Path("services/api/mml_api.py"),
}

REQUIRED_CANONICAL_SNIPPETS = {
    Path("services/api/app/api/v1/router.py"): 'include_router(ai.router, prefix="/ai"',
    Path("services/api/main.py"): 'app.include_router(api_router, prefix="/api/v1")',
}


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _scan_route_decorators(repo_root: Path) -> List[Tuple[Path, str, int]]:
    """Return all matching chat route decorators under services/api."""
    results: List[Tuple[Path, str, int]] = []
    search_root = repo_root / "services" / "api"

    if not search_root.exists():
        return results

    for py_file in sorted(search_root.rglob("*.py")):
        text = py_file.read_text(encoding="utf-8")
        rel_path = py_file.relative_to(repo_root)
        for match in ROUTE_DECORATOR_RE.finditer(text):
            results.append((rel_path, match.group("route"), _line_number(text, match.start())))

    return results


def run_governance_check(repo_root: Path) -> List[str]:
    """Return validation errors. Empty list means pass."""
    errors: List[str] = []

    # Canonical wiring must remain intact.
    for rel_path, snippet in REQUIRED_CANONICAL_SNIPPETS.items():
        file_path = repo_root / rel_path
        if not file_path.exists():
            errors.append(f"Missing required file: {rel_path}")
            continue

        text = file_path.read_text(encoding="utf-8")
        if snippet not in text:
            errors.append(f"Required canonical wiring missing in {rel_path}: {snippet}")

    occurrences = _scan_route_decorators(repo_root)

    canonical_relative = [
        (path, line)
        for path, route, line in occurrences
        if route == "/chat" and path == CANONICAL_CHAT_FILE
    ]

    if len(canonical_relative) != 1:
        errors.append(
            "Canonical relative chat route must appear exactly once in "
            f"{CANONICAL_CHAT_FILE}; found {len(canonical_relative)}"
        )

    for path, route, line in occurrences:
        if route == "/chat" and path != CANONICAL_CHAT_FILE:
            errors.append(f"Non-canonical /chat route found at {path}:{line}")

        if route == "/api/v1/ai/chat" and path not in ALLOWED_LEGACY_ABSOLUTE_FILES:
            errors.append(f"Unknown absolute chat route found at {path}:{line}")

    return errors


def main(argv: List[str]) -> int:
    repo_root = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parents[1]
    errors = run_governance_check(repo_root)

    if errors:
        print("[FAIL] Canonical chat governance check failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print("[PASS] Canonical chat governance check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
