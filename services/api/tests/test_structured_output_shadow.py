from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/api/app/lib/ai/structured_output.py"

_spec = importlib.util.spec_from_file_location("structured_output", MODULE_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load module from {MODULE_PATH}")

_structured_output = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _structured_output
try:
    _spec.loader.exec_module(_structured_output)
except ModuleNotFoundError as exc:
    if exc.name == "pydantic":
        raise unittest.SkipTest("pydantic is not installed in this local test environment") from exc
    raise

parse_structured_model_output = _structured_output.parse_structured_model_output


VALID_STRUCTURED_JSON = """{
  "version": "1.0",
  "action": "respond",
  "assistant_message": "Hello",
  "questions": [],
  "generation_request": null,
  "revision_request": null,
  "state_patch": {},
  "meta": {"needs_summary": false}
}"""


class StructuredOutputShadowTests(unittest.TestCase):
    def test_direct_parse_success_without_repair(self) -> None:
        result = parse_structured_model_output(VALID_STRUCTURED_JSON, max_repair_attempts=1)
        self.assertTrue(result.success)
        self.assertFalse(result.repaired)
        self.assertEqual(result.repair_attempts, 0)
        self.assertEqual(result.parsed.action, "respond")

    def test_repair_parse_success_from_fenced_json(self) -> None:
        fenced = f"Model says:\n```json\n{VALID_STRUCTURED_JSON}\n```"
        result = parse_structured_model_output(fenced, max_repair_attempts=1)
        self.assertTrue(result.success)
        self.assertTrue(result.repaired)
        self.assertEqual(result.repair_attempts, 1)

    def test_parse_failure_does_not_raise(self) -> None:
        result = parse_structured_model_output("not-json", max_repair_attempts=1)
        self.assertFalse(result.success)
        self.assertEqual(result.repair_attempts, 1)
        self.assertIsNotNone(result.error)

    def test_contract_validation_failure_returns_parse_failure(self) -> None:
        invalid_contract_json = "{\"action\": \"respond\"}"
        result = parse_structured_model_output(invalid_contract_json, max_repair_attempts=1)
        self.assertFalse(result.success)
        self.assertEqual(result.repair_attempts, 1)
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
