from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.errors import (  # noqa: E402
    NonRetryableAppError,
    RetryableAppError,
    classify_exception,
)
from app.lib.observability.http_metrics import HttpRequestMetrics  # noqa: E402


class ObservabilityPhase0Tests(unittest.TestCase):
    def test_http_metrics_snapshot_includes_percentiles_and_status_breakdown(self) -> None:
        metrics = HttpRequestMetrics(sample_limit=100)

        for duration in [10, 20, 30, 40, 50]:
            metrics.start_request()
            metrics.finish_request(
                method="GET",
                route_path="/api/v1/projects/{project_id}",
                status_code=200,
                duration_ms=duration,
            )

        metrics.start_request()
        metrics.finish_request(
            method="GET",
            route_path="/api/v1/projects/{project_id}",
            status_code=500,
            duration_ms=80,
            error_type="RuntimeError",
        )

        snapshot = metrics.snapshot()
        self.assertIn("totals", snapshot)
        self.assertEqual(snapshot["totals"]["requests"], 6)

        endpoint = snapshot["endpoints"][0]
        self.assertEqual(endpoint["count"], 6)
        self.assertEqual(endpoint["errors"], 1)
        self.assertGreater(endpoint["p50_ms"], 0)
        self.assertGreaterEqual(endpoint["p95_ms"], endpoint["p50_ms"])
        self.assertEqual(endpoint["status_codes"]["classes"]["2xx"], 5)
        self.assertEqual(endpoint["status_codes"]["classes"]["5xx"], 1)

    def test_error_classification_identifies_retryable_and_non_retryable(self) -> None:
        retryable = classify_exception(RetryableAppError("temporary issue"))
        self.assertTrue(retryable.retryable)
        self.assertEqual(retryable.error_code, "retryable_error")

        non_retryable = classify_exception(NonRetryableAppError("invalid payload"))
        self.assertFalse(non_retryable.retryable)
        self.assertEqual(non_retryable.error_code, "non_retryable_error")

        timeout_classification = classify_exception(TimeoutError("timed out"))
        self.assertTrue(timeout_classification.retryable)
        self.assertEqual(timeout_classification.error_code, "transient_dependency_failure")


if __name__ == "__main__":
    unittest.main()
