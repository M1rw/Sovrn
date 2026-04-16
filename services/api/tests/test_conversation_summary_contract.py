from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "app/lib/ai/conversation_summary.py"

_spec = importlib.util.spec_from_file_location("conversation_summary", MODULE_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load module from {MODULE_PATH}")

_conversation_summary = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _conversation_summary
try:
    _spec.loader.exec_module(_conversation_summary)
except ModuleNotFoundError as exc:
    if exc.name == "pydantic":
        raise unittest.SkipTest("pydantic is not installed in this local test environment") from exc
    raise


parse_conversation_summary_output = _conversation_summary.parse_conversation_summary_output
should_trigger_conversation_summary = _conversation_summary.should_trigger_conversation_summary


class ConversationSummaryContractTests(unittest.TestCase):
    def test_trigger_deterministic_at_exact_interval_without_prior_summary(self) -> None:
        decision = should_trigger_conversation_summary(
            current_turn_index=6,
            latest_summary_to_turn_index=None,
            trigger_every_turns=6,
        )
        self.assertTrue(decision.should_trigger)
        self.assertEqual(decision.from_turn_index, 1)
        self.assertEqual(decision.to_turn_index, 6)

    def test_trigger_skips_when_window_is_too_small(self) -> None:
        decision = should_trigger_conversation_summary(
            current_turn_index=5,
            latest_summary_to_turn_index=None,
            trigger_every_turns=6,
        )
        self.assertFalse(decision.should_trigger)
        self.assertEqual(decision.reason, "window_too_small")

    def test_trigger_resumes_from_last_summary_boundary(self) -> None:
        decision = should_trigger_conversation_summary(
            current_turn_index=10,
            latest_summary_to_turn_index=4,
            trigger_every_turns=6,
        )
        self.assertTrue(decision.should_trigger)
        self.assertEqual(decision.from_turn_index, 5)
        self.assertEqual(decision.to_turn_index, 10)

    def test_trigger_waits_until_next_interval_boundary(self) -> None:
        decision = should_trigger_conversation_summary(
            current_turn_index=11,
            latest_summary_to_turn_index=4,
            trigger_every_turns=6,
        )
        self.assertFalse(decision.should_trigger)
        self.assertEqual(decision.reason, "interval_not_reached")

    def test_valid_summary_payload_passes_contract(self) -> None:
        payload = {
            "version": "1.0",
            "non_authoritative": True,
            "from_turn_index": 1,
            "to_turn_index": 6,
            "summary": "User asked for updates and assistant responded with implementation steps.",
            "key_points": ["User requested phase-only work", "Assistant maintained fail-open behavior"],
            "open_questions": [],
            "meta": {"source": "unit_test"},
        }
        result = parse_conversation_summary_output(payload)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.parsed)
        self.assertTrue(result.parsed.non_authoritative)

    def test_invalid_non_authoritative_flag_is_rejected_safely(self) -> None:
        payload = {
            "version": "1.0",
            "non_authoritative": False,
            "from_turn_index": 1,
            "to_turn_index": 6,
            "summary": "This should fail validation.",
            "key_points": [],
            "open_questions": [],
            "meta": {},
        }
        result = parse_conversation_summary_output(payload)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    def test_invalid_turn_range_is_rejected_safely(self) -> None:
        payload = {
            "version": "1.0",
            "non_authoritative": True,
            "from_turn_index": 8,
            "to_turn_index": 6,
            "summary": "This should fail validation.",
            "key_points": [],
            "open_questions": [],
            "meta": {},
        }
        result = parse_conversation_summary_output(payload)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
