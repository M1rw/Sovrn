"""Prompt registry loader for versioned markdown prompt modules.

This module provides deterministic module ordering, required-module validation,
and checksum validation for prompt artifacts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


class PromptRegistryValidationError(ValueError):
    """Raised when prompt registry validation fails."""


@dataclass(frozen=True)
class PromptModuleMetadata:
    """Registry metadata for one prompt module."""

    module_id: str
    version: str
    file: str
    order: int
    required: bool
    checksum_sha256: str

    def absolute_path(self, prompts_root: Path) -> Path:
        return prompts_root / self.file


@dataclass(frozen=True)
class PromptRegistry:
    """Validated prompt registry."""

    schema_version: str
    required_modules: tuple[str, ...]
    modules: tuple[PromptModuleMetadata, ...]
    prompts_root: Path

    def ordered_modules(self) -> tuple[PromptModuleMetadata, ...]:
        """Return modules in deterministic order."""
        return tuple(sorted(self.modules, key=lambda item: (item.order, item.module_id)))


class PromptRegistryLoader:
    """Load and validate prompt registry metadata."""

    def __init__(self, prompts_root: Path | None = None):
        self.prompts_root = prompts_root or (Path(__file__).resolve().parent / "prompts")

    def default_registry_path(self) -> Path:
        return self.prompts_root / "registry.json"

    def load(self, registry_path: Path | None = None) -> PromptRegistry:
        """Load, parse, and validate the prompt registry."""
        registry_file = registry_path or self.default_registry_path()
        if not registry_file.exists():
            raise PromptRegistryValidationError(f"Registry file not found: {registry_file}")

        raw = json.loads(registry_file.read_text(encoding="utf-8"))
        modules: List[PromptModuleMetadata] = []
        for entry in raw.get("modules", []):
            modules.append(
                PromptModuleMetadata(
                    module_id=entry["id"],
                    version=entry["version"],
                    file=entry["file"],
                    order=int(entry["order"]),
                    required=bool(entry.get("required", False)),
                    checksum_sha256=entry["checksum_sha256"],
                )
            )

        registry = PromptRegistry(
            schema_version=str(raw.get("schema_version", "")),
            required_modules=tuple(raw.get("required_modules", [])),
            modules=tuple(modules),
            prompts_root=registry_file.parent,
        )
        self._validate_registry(registry)
        return registry

    def assemble(self, module_ids: Iterable[str] | None = None, registry_path: Path | None = None) -> str:
        """Assemble selected prompt modules in deterministic order."""
        registry = self.load(registry_path)
        modules_by_id = {module.module_id: module for module in registry.modules}

        if module_ids is None:
            selected = list(registry.ordered_modules())
        else:
            requested = list(module_ids)
            missing = [module_id for module_id in requested if module_id not in modules_by_id]
            if missing:
                raise PromptRegistryValidationError(f"Unknown module ids requested: {missing}")
            selected = sorted(
                (modules_by_id[module_id] for module_id in requested),
                key=lambda item: (item.order, item.module_id),
            )

        chunks = []
        for module in selected:
            module_path = module.absolute_path(registry.prompts_root)
            chunks.append(module_path.read_text(encoding="utf-8").rstrip())

        return "\n\n".join(chunks)

    def _validate_registry(self, registry: PromptRegistry) -> None:
        if registry.schema_version != "1.0":
            raise PromptRegistryValidationError(
                f"Unsupported prompt registry schema_version: {registry.schema_version}"
            )

        if not registry.modules:
            raise PromptRegistryValidationError("Prompt registry must define at least one module")

        module_ids = [module.module_id for module in registry.modules]
        if len(module_ids) != len(set(module_ids)):
            raise PromptRegistryValidationError("Duplicate module id detected in prompt registry")

        required_set = set(registry.required_modules)
        available_set = set(module_ids)
        missing_required = sorted(required_set - available_set)
        if missing_required:
            raise PromptRegistryValidationError(
                f"Required modules missing from registry: {missing_required}"
            )

        for module in registry.modules:
            module_path = module.absolute_path(registry.prompts_root)
            if not module_path.exists():
                raise PromptRegistryValidationError(f"Prompt module file not found: {module.file}")

            if module.module_id in required_set and not module.required:
                raise PromptRegistryValidationError(
                    f"Module {module.module_id} is required but not marked required=true"
                )

            checksum = _sha256_file(module_path)
            if checksum != module.checksum_sha256:
                raise PromptRegistryValidationError(
                    f"Checksum mismatch for {module.file}: expected {module.checksum_sha256}, got {checksum}"
                )



def _sha256_file(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()
