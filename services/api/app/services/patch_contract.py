"""Patch-contract conflict resolver and rollback support.

Applies deterministic patch operations to an in-memory file map. If an
operation cannot be safely resolved, the resolver returns the original file map
with a rolled-back result.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Literal

from app.schemas import PatchContractRequest

PatchConflictCode = Literal["missing_file", "hash_mismatch", "invalid_range"]


@dataclass(slots=True)
class PatchConflict:
    """Represents one conflict encountered while applying patch operations."""

    operation_index: int
    path: str
    op: str
    code: PatchConflictCode
    message: str
    fallback_applied: bool = False


@dataclass(slots=True)
class PatchResolutionResult:
    """Result of resolving a patch contract against a file map."""

    applied: bool
    rolled_back: bool
    applied_operations: int
    files: dict[str, str]
    conflicts: list[PatchConflict]


def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class StructuralAstNode:
    """Minimal structural AST node used for language syntax guards."""

    opener: str
    closer: str
    start: int
    end: int


@dataclass(slots=True)
class StructuralAst:
    """Structural AST model for bracket-based language profiles."""

    profile: str
    nodes: list[StructuralAstNode]


def _resolve_range_replace(content: str, *, start: int, end: int, replacement: str) -> str | None:
    if start < 0 or end < start:
        return None
    if end > len(content):
        return None
    return f"{content[:start]}{replacement}{content[end:]}"


def _rollback_result(base_files: dict[str, str], conflicts: list[PatchConflict]) -> PatchResolutionResult:
    return PatchResolutionResult(
        applied=False,
        rolled_back=True,
        applied_operations=0,
        files=dict(base_files),
        conflicts=conflicts,
    )


def _resolve_language_profile(path: str, language: str | None) -> str | None:
    if isinstance(language, str) and language.strip():
        normalized_language = language.strip().lower()
        if normalized_language in {"ts", "tsx", "typescript"}:
            return "ts"
        if normalized_language in {"js", "jsx", "javascript"}:
            return "js"
        if normalized_language in {"json", "css"}:
            return normalized_language

    extension = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if extension in {"ts", "tsx"}:
        return "ts"
    if extension in {"js", "jsx"}:
        return "js"
    if extension in {"json", "css"}:
        return extension

    return None


def _get_string_delimiters(profile: str) -> tuple[str, ...]:
    if profile == "json":
        return ('"',)
    if profile in {"js", "ts"}:
        return ('"', "'", "`")
    return ('"', "'")


def _sanitize_for_structural_parse(content: str, profile: str) -> str:
    string_delimiters = _get_string_delimiters(profile)
    allow_line_comments = profile in {"js", "ts"}
    sanitized = list(content)

    in_string: str | None = None
    in_block_comment = False
    in_line_comment = False
    escaped = False

    index = 0
    length = len(content)

    while index < length:
        char = content[index]
        next_char = content[index + 1] if index + 1 < length else ""

        if in_string is not None:
            sanitized[index] = " "
            if escaped:
                escaped = False
                index += 1
                continue
            if char == "\\":
                escaped = True
                index += 1
                continue
            if char == in_string:
                in_string = None
            index += 1
            continue

        if in_block_comment:
            sanitized[index] = " "
            if char == "*" and next_char == "/":
                sanitized[index + 1] = " "
                in_block_comment = False
                index += 2
                continue
            index += 1
            continue

        if in_line_comment:
            if char != "\n":
                sanitized[index] = " "
                index += 1
                continue
            in_line_comment = False
            index += 1
            continue

        if char in string_delimiters:
            in_string = char
            sanitized[index] = " "
            index += 1
            continue

        if allow_line_comments and char == "/" and next_char == "/":
            sanitized[index] = " "
            sanitized[index + 1] = " "
            in_line_comment = True
            index += 2
            continue

        if char == "/" and next_char == "*":
            sanitized[index] = " "
            sanitized[index + 1] = " "
            in_block_comment = True
            index += 2
            continue

        index += 1

    if in_string is not None:
        raise ValueError(f"Unterminated string literal detected for profile '{profile}'")
    if in_block_comment:
        raise ValueError(f"Unterminated block comment detected for profile '{profile}'")

    return "".join(sanitized)


def _parse_structural_ast(content: str, profile: str) -> StructuralAst:
    bracket_pairs = {
        "(": ")",
        "[": "]",
        "{": "}",
    }
    closing_to_opening = {
        ")": "(",
        "]": "[",
        "}": "{",
    }
    allowed_closers_by_opening = {
        "(": ")",
        "[": "]",
        "{": "}",
    }

    sanitized = _sanitize_for_structural_parse(content, profile)
    stack: list[tuple[str, int]] = []
    nodes: list[StructuralAstNode] = []

    for index, char in enumerate(sanitized):
        if char in bracket_pairs:
            stack.append((char, index))
            continue

        if char in closing_to_opening:
            if not stack:
                raise ValueError(
                    f"Unexpected closing delimiter '{char}' at offset {index} for profile '{profile}'"
                )

            opening, start = stack.pop()
            expected = allowed_closers_by_opening[opening]
            if expected != char:
                raise ValueError(
                    "Mismatched delimiter "
                    f"'{opening}' at offset {start} closed by '{char}' at offset {index}"
                )

            nodes.append(
                StructuralAstNode(opener=opening, closer=char, start=start, end=index)
            )

    if stack:
        opening, start = stack[-1]
        raise ValueError(
            f"Unclosed delimiter '{opening}' at offset {start} for profile '{profile}'"
        )

    return StructuralAst(profile=profile, nodes=nodes)


def _parse_ast(content: str, profile: str) -> object:
    if profile == "json":
        return json.loads(content)
    if profile in {"ts", "js", "css"}:
        return _parse_structural_ast(content, profile)

    raise ValueError(f"Unsupported AST profile '{profile}'")


def _validate_range_transform_ast(
    *,
    path: str,
    language: str | None,
    source_content: str,
    transformed_content: str,
) -> str | None:
    profile = _resolve_language_profile(path, language)
    if profile is None:
        if isinstance(language, str) and language.strip():
            return (
                "AST profile unsupported for declared language "
                f"'{language}' on {path}; requires safe rewrite fallback"
            )
        return None

    try:
        _parse_ast(source_content, profile)
    except Exception as exc:
        return f"AST source parse failed for {path}: {exc}"

    try:
        _parse_ast(transformed_content, profile)
    except Exception as exc:
        return f"AST transformed parse failed for {path}: {exc}"

    return None


def _normalize_text_content(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    normalized = "\n".join(lines)

    if normalized and not normalized.endswith("\n"):
        normalized = f"{normalized}\n"

    return normalized


def _format_json_content(content: str) -> str:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return _normalize_text_content(content)

    return f"{json.dumps(parsed, indent=2, sort_keys=True, ensure_ascii=False)}\n"


def _resolve_format_profile(path: str, language: str | None) -> str | None:
    return _resolve_language_profile(path, language)


def _apply_deterministic_formatter(path: str, content: str, language: str | None) -> str:
    profile = _resolve_format_profile(path, language)
    if profile is None:
        return content

    if profile == "json":
        return _format_json_content(content)

    return _normalize_text_content(content)


def resolve_patch_contract_files(
    files: dict[str, str],
    contract: PatchContractRequest,
) -> PatchResolutionResult:
    """Resolve patch operations with conflict detection and rollback support."""
    base_files = dict(files)
    working_files = dict(base_files)
    conflicts: list[PatchConflict] = []
    applied_operations = 0
    touched_paths: set[str] = set()
    language_by_path: dict[str, str] = {}

    for operation_index, operation in enumerate(contract.operations):
        existing_content = working_files.get(operation.path)

        touched_paths.add(operation.path)
        if isinstance(operation.language, str) and operation.language.strip():
            language_by_path[operation.path] = operation.language.strip()

        if operation.expected_sha256 is not None:
            content_for_hash = existing_content or ""
            if _sha256_text(content_for_hash) != operation.expected_sha256:
                conflicts.append(
                    PatchConflict(
                        operation_index=operation_index,
                        path=operation.path,
                        op=operation.op,
                        code="hash_mismatch",
                        message="Patch expected_sha256 does not match current file content",
                    )
                )
                return _rollback_result(base_files, conflicts)

        if operation.op == "replace_file":
            working_files[operation.path] = operation.content
            applied_operations += 1
            continue

        # replace_range path
        if existing_content is None:
            conflict = PatchConflict(
                operation_index=operation_index,
                path=operation.path,
                op=operation.op,
                code="missing_file",
                message="Range patch target file does not exist",
            )
            conflicts.append(conflict)
            if contract.fallback_mode == "safe_rewrite":
                conflict.fallback_applied = True
                working_files[operation.path] = operation.content
                applied_operations += 1
                continue
            return _rollback_result(base_files, conflicts)

        if operation.range is None:
            # Schema validation already forbids this, but keep fail-safe behavior.
            conflicts.append(
                PatchConflict(
                    operation_index=operation_index,
                    path=operation.path,
                    op=operation.op,
                    code="invalid_range",
                    message="Range patch is missing required range payload",
                )
            )
            return _rollback_result(base_files, conflicts)

        patched_content = _resolve_range_replace(
            existing_content,
            start=operation.range.start,
            end=operation.range.end,
            replacement=operation.content,
        )

        if patched_content is None:
            conflict = PatchConflict(
                operation_index=operation_index,
                path=operation.path,
                op=operation.op,
                code="invalid_range",
                message="Range patch bounds are outside file content length",
            )
            conflicts.append(conflict)
            if contract.fallback_mode == "safe_rewrite":
                conflict.fallback_applied = True
                working_files[operation.path] = operation.content
                applied_operations += 1
                continue
            return _rollback_result(base_files, conflicts)

        ast_validation_error = _validate_range_transform_ast(
            path=operation.path,
            language=operation.language,
            source_content=existing_content,
            transformed_content=patched_content,
        )
        if ast_validation_error is not None:
            conflict = PatchConflict(
                operation_index=operation_index,
                path=operation.path,
                op=operation.op,
                code="invalid_range",
                message=ast_validation_error,
            )
            conflicts.append(conflict)
            if contract.fallback_mode == "safe_rewrite":
                conflict.fallback_applied = True
                if "AST profile unsupported" in ast_validation_error:
                    working_files[operation.path] = patched_content
                else:
                    working_files[operation.path] = operation.content
                applied_operations += 1
                continue
            return _rollback_result(base_files, conflicts)

        working_files[operation.path] = patched_content
        applied_operations += 1

    for path in sorted(touched_paths):
        if path not in working_files:
            continue

        working_files[path] = _apply_deterministic_formatter(
            path,
            working_files[path],
            language_by_path.get(path),
        )

    return PatchResolutionResult(
        applied=True,
        rolled_back=False,
        applied_operations=applied_operations,
        files=working_files,
        conflicts=conflicts,
    )
