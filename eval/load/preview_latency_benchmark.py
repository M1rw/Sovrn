"""
Phase 2 preview runtime latency benchmark.

Measures end-to-end preview bootstrap latency across these steps:
1) Create preview session
2) Verify preview session
3) Fetch preview artifact
4) Open preview event stream and wait for first preview.updated event

Outputs p50/p95/p99 metrics and fails non-zero when p95 total latency exceeds target.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


@dataclass
class IterationResult:
    iteration: int
    success: bool
    session_ms: float
    verify_ms: float
    artifact_ms: float
    stream_first_update_ms: float
    total_ms: float
    generation_id: str
    generation_version: int
    error: str = ""


@dataclass
class SummaryStats:
    count: int
    successful: int
    failed: int
    success_rate: float
    p50_total_ms: float
    p95_total_ms: float
    p99_total_ms: float
    p95_stream_first_update_ms: float
    mean_total_ms: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 2 preview latency benchmark")
    parser.add_argument("--base-url", default=os.getenv("SOVRN_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.getenv("SOVRN_TOKEN", ""))
    parser.add_argument("--project-id", default=os.getenv("SOVRN_PROJECT_ID", ""))
    parser.add_argument("--generation-id", default=os.getenv("SOVRN_GENERATION_ID", ""))
    parser.add_argument("--entrypoint", default=os.getenv("SOVRN_ENTRYPOINT", "index.html"))
    parser.add_argument("--iterations", type=int, default=int(os.getenv("SOVRN_PREVIEW_BENCH_ITERATIONS", "30")))
    parser.add_argument("--warmup", type=int, default=int(os.getenv("SOVRN_PREVIEW_BENCH_WARMUP", "3")))
    parser.add_argument("--poll-interval-ms", type=int, default=int(os.getenv("SOVRN_PREVIEW_BENCH_POLL_MS", "250")))
    parser.add_argument("--stream-timeout-ms", type=int, default=int(os.getenv("SOVRN_PREVIEW_BENCH_STREAM_TIMEOUT_MS", "6000")))
    parser.add_argument("--request-timeout-ms", type=int, default=int(os.getenv("SOVRN_PREVIEW_BENCH_REQUEST_TIMEOUT_MS", "15000")))
    parser.add_argument("--target-p95-ms", type=float, default=float(os.getenv("SOVRN_PREVIEW_TARGET_P95_MS", "1500")))
    parser.add_argument(
        "--output",
        default=os.getenv("SOVRN_PREVIEW_BENCH_OUTPUT", "eval/load/phase2_preview_latency_report.json"),
    )
    return parser.parse_args()


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (len(sorted_values) - 1) * (p / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[lower]

    lower_value = sorted_values[lower]
    upper_value = sorted_values[upper]
    return lower_value + (upper_value - lower_value) * (rank - lower)


def ms_since(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def resolve_generation_id(client: httpx.Client, project_id: str, explicit_generation_id: str) -> str:
    if explicit_generation_id:
        return explicit_generation_id

    response = client.get(f"/api/v1/projects/{project_id}")
    response.raise_for_status()
    payload = response.json()
    generations = payload.get("generations")
    if not isinstance(generations, list) or not generations:
        raise RuntimeError(
            "Project has no generations. Provide --generation-id or create a completed generation first."
        )

    latest = max(generations, key=lambda item: int(item.get("version", 0)))
    generation_id = latest.get("id")
    if not isinstance(generation_id, str) or not generation_id:
        raise RuntimeError("Unable to resolve latest generation id from project response")

    return generation_id


def read_first_preview_updated_event(response: httpx.Response, timeout_ms: int) -> tuple[str, int]:
    started_at = time.perf_counter()
    event_name = ""
    data_lines: list[str] = []

    for line in response.iter_lines():
        if line is None:
            continue

        if ms_since(started_at) > timeout_ms:
            raise TimeoutError("Timed out waiting for preview.updated event")

        stripped = line.strip()
        if not stripped:
            if event_name == "preview.updated" and data_lines:
                payload = json.loads("\n".join(data_lines))
                generation_id = str(payload.get("generation_id") or "")
                generation_version = int(payload.get("generation_version") or 0)
                if not generation_id:
                    raise RuntimeError("preview.updated payload missing generation_id")
                if generation_version < 1:
                    raise RuntimeError("preview.updated payload missing valid generation_version")
                return generation_id, generation_version

            event_name = ""
            data_lines = []
            continue

        if stripped.startswith(":"):
            continue

        if stripped.startswith("event:"):
            event_name = stripped.split(":", 1)[1].strip()
            continue

        if stripped.startswith("data:"):
            data_lines.append(stripped.split(":", 1)[1].lstrip())
            continue

    raise RuntimeError("Preview stream ended before preview.updated event was received")


def run_iteration(
    client: httpx.Client,
    project_id: str,
    generation_id: str,
    entrypoint: str,
    poll_interval_ms: int,
    stream_timeout_ms: int,
    iteration: int,
) -> IterationResult:
    overall_start = time.perf_counter()
    try:
        session_start = time.perf_counter()
        session_response = client.post(
            f"/api/v1/projects/{project_id}/preview-session",
            json={
                "generation_id": generation_id,
                "entrypoint": entrypoint,
                "ttl_seconds": 600,
            },
        )
        session_response.raise_for_status()
        session_payload = session_response.json()
        session_ms = ms_since(session_start)

        preview_token = session_payload.get("token")
        if not isinstance(preview_token, str) or not preview_token:
            raise RuntimeError("preview-session response missing token")

        verify_start = time.perf_counter()
        verify_response = client.post(
            f"/api/v1/projects/{project_id}/preview-session/verify",
            json={
                "token": preview_token,
                "generation_id": generation_id,
                "entrypoint": entrypoint,
            },
        )
        verify_response.raise_for_status()
        verify_payload = verify_response.json()
        verify_ms = ms_since(verify_start)

        artifact_endpoint = verify_payload.get("artifact_endpoint")
        if not isinstance(artifact_endpoint, str) or not artifact_endpoint:
            raise RuntimeError("preview-session verify response missing artifact_endpoint")

        artifact_start = time.perf_counter()
        artifact_response = client.get(
            artifact_endpoint,
            headers={"Authorization": f"Bearer {preview_token}"},
        )
        artifact_response.raise_for_status()
        artifact_payload = artifact_response.json()
        artifact_ms = ms_since(artifact_start)

        artifact_generation_id = str(artifact_payload.get("generation_id") or "")
        if artifact_generation_id and artifact_generation_id != generation_id:
            generation_id = artifact_generation_id

        stream_start = time.perf_counter()
        with client.stream(
            "GET",
            f"/api/v1/projects/{project_id}/preview-events",
            params={
                "generation_id": generation_id,
                "entrypoint": entrypoint,
                "preview_token": preview_token,
                "poll_interval_ms": poll_interval_ms,
            },
        ) as stream_response:
            stream_response.raise_for_status()
            stream_generation_id, stream_generation_version = read_first_preview_updated_event(
                stream_response,
                timeout_ms=stream_timeout_ms,
            )

        stream_first_update_ms = ms_since(stream_start)
        total_ms = ms_since(overall_start)

        return IterationResult(
            iteration=iteration,
            success=True,
            session_ms=session_ms,
            verify_ms=verify_ms,
            artifact_ms=artifact_ms,
            stream_first_update_ms=stream_first_update_ms,
            total_ms=total_ms,
            generation_id=stream_generation_id,
            generation_version=stream_generation_version,
        )
    except Exception as exc:  # pragma: no cover - benchmark runner error path
        return IterationResult(
            iteration=iteration,
            success=False,
            session_ms=0.0,
            verify_ms=0.0,
            artifact_ms=0.0,
            stream_first_update_ms=0.0,
            total_ms=ms_since(overall_start),
            generation_id=generation_id,
            generation_version=0,
            error=str(exc),
        )


def build_summary(results: list[IterationResult]) -> SummaryStats:
    successful = [item for item in results if item.success]
    total_latencies = [item.total_ms for item in successful]
    stream_latencies = [item.stream_first_update_ms for item in successful]

    count = len(results)
    success_count = len(successful)
    failed_count = count - success_count
    success_rate = (success_count / count) if count else 0.0

    mean_total_ms = (sum(total_latencies) / len(total_latencies)) if total_latencies else 0.0

    return SummaryStats(
        count=count,
        successful=success_count,
        failed=failed_count,
        success_rate=success_rate,
        p50_total_ms=percentile(total_latencies, 50),
        p95_total_ms=percentile(total_latencies, 95),
        p99_total_ms=percentile(total_latencies, 99),
        p95_stream_first_update_ms=percentile(stream_latencies, 95),
        mean_total_ms=mean_total_ms,
    )


def main() -> int:
    args = parse_args()

    if not args.token:
        print("ERROR: --token or SOVRN_TOKEN is required", file=sys.stderr)
        return 2

    if not args.project_id:
        print("ERROR: --project-id or SOVRN_PROJECT_ID is required", file=sys.stderr)
        return 2

    base_url = args.base_url.rstrip("/")
    timeout_seconds = max(args.request_timeout_ms / 1000.0, 1.0)

    headers = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json",
    }

    client = httpx.Client(
        base_url=base_url,
        headers=headers,
        timeout=httpx.Timeout(timeout_seconds),
    )

    try:
        generation_id = resolve_generation_id(client, args.project_id, args.generation_id)
        print(f"Resolved generation id: {generation_id}")

        for iteration in range(1, args.warmup + 1):
            warmup_result = run_iteration(
                client=client,
                project_id=args.project_id,
                generation_id=generation_id,
                entrypoint=args.entrypoint,
                poll_interval_ms=args.poll_interval_ms,
                stream_timeout_ms=args.stream_timeout_ms,
                iteration=iteration,
            )
            if not warmup_result.success:
                print(f"Warmup {iteration} failed: {warmup_result.error}")
            else:
                print(
                    f"Warmup {iteration}: total={warmup_result.total_ms:.2f}ms "
                    f"stream_first_update={warmup_result.stream_first_update_ms:.2f}ms"
                )

        results: list[IterationResult] = []
        for iteration in range(1, args.iterations + 1):
            result = run_iteration(
                client=client,
                project_id=args.project_id,
                generation_id=generation_id,
                entrypoint=args.entrypoint,
                poll_interval_ms=args.poll_interval_ms,
                stream_timeout_ms=args.stream_timeout_ms,
                iteration=iteration,
            )
            results.append(result)

            if result.success:
                print(
                    f"Iteration {iteration:02d}: total={result.total_ms:.2f}ms "
                    f"session={result.session_ms:.2f}ms verify={result.verify_ms:.2f}ms "
                    f"artifact={result.artifact_ms:.2f}ms stream={result.stream_first_update_ms:.2f}ms"
                )
            else:
                print(f"Iteration {iteration:02d}: failed ({result.error})")

        summary = build_summary(results)
        passed = summary.p95_total_ms <= args.target_p95_ms and summary.failed == 0

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "benchmark": "phase2_preview_latency",
            "target": {
                "p95_total_ms_max": args.target_p95_ms,
            },
            "config": {
                "base_url": base_url,
                "project_id": args.project_id,
                "generation_id": generation_id,
                "entrypoint": args.entrypoint,
                "iterations": args.iterations,
                "warmup": args.warmup,
                "poll_interval_ms": args.poll_interval_ms,
                "stream_timeout_ms": args.stream_timeout_ms,
                "request_timeout_ms": args.request_timeout_ms,
            },
            "summary": asdict(summary),
            "passed": passed,
            "results": [asdict(item) for item in results],
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print("\nSummary")
        print(f"- successful: {summary.successful}/{summary.count}")
        print(f"- p50 total: {summary.p50_total_ms:.2f}ms")
        print(f"- p95 total: {summary.p95_total_ms:.2f}ms")
        print(f"- p99 total: {summary.p99_total_ms:.2f}ms")
        print(f"- p95 stream first update: {summary.p95_stream_first_update_ms:.2f}ms")
        print(f"- target p95 <= {args.target_p95_ms:.2f}ms: {'PASS' if passed else 'FAIL'}")
        print(f"- report: {output_path}")

        return 0 if passed else 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
