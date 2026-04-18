#!/usr/bin/env python3
"""Rearrange phase audit for production-hardening markers.

Scans repository text files and reports patterns that often indicate
non-production placeholders, phase-specific naming, or temporary language.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".env",
    ".ini",
    ".cfg",
    ".conf",
    ".sql",
    ".ps1",
    ".sh",
    ".css",
    ".html",
    ".txt",
}

EXCLUDED_DIR_NAMES = {
    ".git",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "archive",
    "legacy",
}

EXCLUDED_FILE_NAMES = {
    "REARRANGE_STAGE1_AUDIT.md",
    "REARRANGE_STAGE2_AUDIT.md",
    "rearrange_audit.py",
}


@dataclass(frozen=True)
class AuditPattern:
    key: str
    title: str
    regex: re.Pattern[str]


PATTERNS: tuple[AuditPattern, ...] = (
    AuditPattern(
        key="phase_prefix",
        title="Phase-Prefixed Naming",
        regex=re.compile(r"\bPHASE4_[A-Z0-9_]*\b|\bphase4\b", re.IGNORECASE),
    ),
    AuditPattern(
        key="mvp_language",
        title="MVP/Prototype Language",
        regex=re.compile(r"\bmvp\b|\bminimum viable\b|\bquick win\b", re.IGNORECASE),
    ),
    AuditPattern(
        key="placeholder_secrets",
        title="Placeholder Secret Markers",
        regex=re.compile(r"change_me|your-password|your_password|replace_me", re.IGNORECASE),
    ),
    AuditPattern(
        key="todo_markers",
        title="TODO/FIXME Markers",
        regex=re.compile(r"\bTODO\b|\bFIXME\b|\bTBD\b"),
    ),
    AuditPattern(
        key="superbase_typo",
        title="Supabase Typo Markers",
        regex=re.compile(r"\bsuperbase\b", re.IGNORECASE),
    ),
)

PHASE_PREFIX_ALLOWED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'AliasChoices\("ORCHESTRATION_[A-Z0-9_]+",\s*"PHASE4_[A-Z0-9_]+"\)'),
    re.compile(r"REARRANGE_STAGE1_AUDIT\.md", re.IGNORECASE),
)


def _is_allowed_finding(path: Path, pattern_key: str, line: str) -> bool:
    if pattern_key != "phase_prefix":
        return False

    normalized_path = str(path).replace("\\", "/")
    if normalized_path.endswith("services/api/app/core/config.py"):
        return True
    if normalized_path.endswith("docs/Plan/PHASED_NEXTGEN_PRODUCTION_PLAN.md"):
        return True

    return any(regex.search(line) for regex in PHASE_PREFIX_ALLOWED_PATTERNS)


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in EXCLUDED_DIR_NAMES for part in rel_parts)


def _iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in EXCLUDED_FILE_NAMES:
            continue
        if _is_excluded(path, root):
            continue
        if path.suffix.lower() not in DEFAULT_TEXT_SUFFIXES:
            continue
        files.append(path)
    return files


def _scan_file(path: Path) -> list[tuple[str, int, str]]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    findings: list[tuple[str, int, str]] = []
    lines = content.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for pattern in PATTERNS:
            if pattern.regex.search(line):
                if _is_allowed_finding(path, pattern.key, line):
                    continue
                snippet = line.strip()
                if len(snippet) > 180:
                    snippet = snippet[:177] + "..."
                findings.append((pattern.key, line_number, snippet))
    return findings


def _build_report(
    root: Path,
    files: list[Path],
    findings_by_file: dict[Path, list[tuple[str, int, str]]],
    report_title: str,
) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    pattern_lookup = {pattern.key: pattern.title for pattern in PATTERNS}

    files_with_findings = sorted(findings_by_file.keys())
    total_findings = sum(len(items) for items in findings_by_file.values())
    folder_set = {
        str(path.relative_to(root).parent).replace("\\", "/")
        for path in files
    }

    pattern_count: Counter[str] = Counter()
    pattern_file_count: defaultdict[str, set[Path]] = defaultdict(set)
    for path, records in findings_by_file.items():
        for key, _, _ in records:
            pattern_count[key] += 1
            pattern_file_count[key].add(path)

    top_files = sorted(
        files_with_findings,
        key=lambda item: len(findings_by_file[item]),
        reverse=True,
    )[:30]

    lines: list[str] = []
    lines.append(f"# {report_title}")
    lines.append("")
    lines.append(f"Generated at: {now}")
    lines.append(f"Repository root: {root}")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Files scanned: {len(files)}")
    lines.append(f"- Folders scanned: {len(folder_set)}")
    lines.append(f"- Files with findings: {len(files_with_findings)}")
    lines.append(f"- Total findings: {total_findings}")
    lines.append("")

    lines.append("## Pattern Summary")
    lines.append("")
    lines.append("| Pattern | Hits | Files |")
    lines.append("| --- | ---: | ---: |")
    for pattern in PATTERNS:
        hits = pattern_count.get(pattern.key, 0)
        file_hits = len(pattern_file_count.get(pattern.key, set()))
        lines.append(f"| {pattern.title} | {hits} | {file_hits} |")
    lines.append("")

    lines.append("## Top Files By Finding Count")
    lines.append("")
    for path in top_files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        lines.append(f"- {rel}: {len(findings_by_file[path])}")
    if not top_files:
        lines.append("- No findings.")
    lines.append("")

    lines.append("## Findings (Sampled)")
    lines.append("")
    for path in top_files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        lines.append(f"### {rel}")
        for key, line_number, snippet in findings_by_file[path][:10]:
            title = pattern_lookup.get(key, key)
            lines.append(f"- [{title}] L{line_number}: {snippet}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Rearrange production-hardening audit.")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root path to scan.",
    )
    parser.add_argument(
        "--output",
        default="docs/Plan/REARRANGE_STAGE2_AUDIT.md",
        help="Output markdown report path.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = (root / args.output).resolve()

    files = [path for path in _iter_text_files(root) if path.resolve() != output]
    findings_by_file: dict[Path, list[tuple[str, int, str]]] = {}
    for path in files:
        findings = _scan_file(path=path)
        if findings:
            findings_by_file[path] = findings

    report_title = "Rearrange Stage 2 Audit"
    report = _build_report(
        root=root,
        files=files,
        findings_by_file=findings_by_file,
        report_title=report_title,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")

    print(f"Scanned {len(files)} files")
    print(f"Files with findings: {len(findings_by_file)}")
    print(f"Report written to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
