from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/api/app/lib/ai/prompt_registry.py"

_spec = importlib.util.spec_from_file_location("prompt_registry", MODULE_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load module from {MODULE_PATH}")

_prompt_registry = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _prompt_registry
_spec.loader.exec_module(_prompt_registry)

PromptRegistryLoader = _prompt_registry.PromptRegistryLoader
PromptRegistryValidationError = _prompt_registry.PromptRegistryValidationError



def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class PromptRegistryLoaderTests(unittest.TestCase):
    def test_load_registry_orders_modules_deterministically(self) -> None:
        loader = PromptRegistryLoader(
            prompts_root=REPO_ROOT / "services/api/app/lib/ai/prompts"
        )
        registry = loader.load()

        ordered_ids = [module.module_id for module in registry.ordered_modules()]
        self.assertEqual(
            ordered_ids,
            [
                "core_identity",
                "website_clarification",
                "generation_readiness",
                "revision_rules",
                "output_contract",
            ],
        )

    def test_required_module_validation_fails_when_required_module_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            _write(temp_root / "modules/core_identity.v1.md", "core")
            registry_path = temp_root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "required_modules": ["core_identity", "output_contract"],
                        "modules": [
                            {
                                "id": "core_identity",
                                "version": "1.0.0",
                                "file": "modules/core_identity.v1.md",
                                "order": 10,
                                "required": True,
                                "checksum_sha256": "0d45f5fd462b8c70bffb10021ac1bcff3f58f29b1faf7568595095427d42812c",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loader = PromptRegistryLoader(prompts_root=temp_root)
            with self.assertRaises(PromptRegistryValidationError):
                loader.load(registry_path)

    def test_checksum_validation_fails_on_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            _write(temp_root / "modules/core_identity.v1.md", "core")
            registry_path = temp_root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "required_modules": ["core_identity"],
                        "modules": [
                            {
                                "id": "core_identity",
                                "version": "1.0.0",
                                "file": "modules/core_identity.v1.md",
                                "order": 10,
                                "required": True,
                                "checksum_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loader = PromptRegistryLoader(prompts_root=temp_root)
            with self.assertRaises(PromptRegistryValidationError):
                loader.load(registry_path)


if __name__ == "__main__":
    unittest.main()
