from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from typing import Deque

from app.core.config import settings


class HttpRequestMetrics:
    """In-memory HTTP request metrics store for observability dashboards."""

    def __init__(self, sample_limit: int = 500) -> None:
        self._sample_limit = sample_limit
        self._durations_ms: dict[tuple[str, str], Deque[float]] = defaultdict(
            lambda: deque(maxlen=sample_limit)
        )
        self._status_counts: dict[tuple[str, str, int], int] = defaultdict(int)
        self._error_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._request_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._total_requests = 0
        self._inflight_requests = 0
        self._lock = Lock()

    def start_request(self) -> None:
        with self._lock:
            self._inflight_requests += 1

    def finish_request(
        self,
        method: str,
        route_path: str,
        status_code: int,
        duration_ms: float,
        error_type: str | None = None,
    ) -> None:
        key = (method.upper(), route_path or "unknown")
        duration_value = max(0.0, float(duration_ms))

        with self._lock:
            self._total_requests += 1
            self._inflight_requests = max(0, self._inflight_requests - 1)
            self._request_counts[key] += 1
            self._durations_ms[key].append(duration_value)
            self._status_counts[(key[0], key[1], int(status_code))] += 1
            if error_type:
                self._error_counts[key] += 1

    def snapshot(self) -> dict:
        with self._lock:
            endpoints = []
            for key, count in sorted(self._request_counts.items()):
                method, route_path = key
                durations = list(self._durations_ms.get(key, []))
                status_breakdown = self._status_summary(method, route_path)
                errors = self._error_counts.get(key, 0)
                endpoints.append(
                    {
                        "method": method,
                        "path": route_path,
                        "count": count,
                        "errors": errors,
                        "error_rate": round((errors / count), 4) if count else 0.0,
                        "p50_ms": round(self._percentile(durations, 0.50), 2),
                        "p95_ms": round(self._percentile(durations, 0.95), 2),
                        "p99_ms": round(self._percentile(durations, 0.99), 2),
                        "status_codes": status_breakdown,
                    }
                )

            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sample_limit": self._sample_limit,
                "totals": {
                    "requests": self._total_requests,
                    "inflight": self._inflight_requests,
                    "tracked_endpoints": len(self._request_counts),
                },
                "endpoints": endpoints,
            }

    def _status_summary(self, method: str, route_path: str) -> dict:
        status_codes: dict[str, int] = {}
        status_classes = {"2xx": 0, "4xx": 0, "5xx": 0}

        for (m, path, status_code), count in self._status_counts.items():
            if m != method or path != route_path:
                continue
            status_codes[str(status_code)] = status_codes.get(str(status_code), 0) + count
            if 200 <= status_code < 300:
                status_classes["2xx"] += count
            elif 400 <= status_code < 500:
                status_classes["4xx"] += count
            elif status_code >= 500:
                status_classes["5xx"] += count

        return {
            "codes": status_codes,
            "classes": status_classes,
        }

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0

        sorted_values = sorted(values)
        if len(sorted_values) == 1:
            return sorted_values[0]

        idx = (len(sorted_values) - 1) * percentile
        lower_idx = int(idx)
        upper_idx = min(lower_idx + 1, len(sorted_values) - 1)
        weight = idx - lower_idx

        lower = sorted_values[lower_idx]
        upper = sorted_values[upper_idx]
        return lower + (upper - lower) * weight


http_request_metrics = HttpRequestMetrics(
    sample_limit=settings.OBSERVABILITY_HTTP_METRICS_SAMPLE_LIMIT
)
