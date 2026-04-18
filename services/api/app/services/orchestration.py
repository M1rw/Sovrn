"""Generation orchestration runtime (AQE + multi-agent loop)."""

from __future__ import annotations

import asyncio
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Literal, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Job, JobStatus


AqeLevel = Literal["Q3", "Q2", "Q1", "Q0"]
LaneName = Literal["interactive", "quality", "background"]
UiQualityMode = Literal["fast", "balanced", "high"]
TargetGenerationMode = Literal["fast", "balanced", "quality"]

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


class OrchestrationCancelledError(RuntimeError):
    """Raised when the active job gets cancelled while processing."""


class OrchestrationBudgetExceededError(RuntimeError):
    """Raised when orchestration exceeds the configured request budget."""


def normalize_ui_quality_mode(value: Optional[str]) -> UiQualityMode:
    if value in ("fast", "balanced", "high"):
        return value
    return "balanced"


def map_ui_quality_to_target_mode(quality_mode: UiQualityMode) -> TargetGenerationMode:
    if quality_mode == "high":
        return "quality"
    return quality_mode


def resolve_generation_lane(_: UiQualityMode) -> LaneName:
    # User-triggered generation stays in the interactive lane by default.
    return "interactive"


def resolve_generation_priority(quality_mode: UiQualityMode, lane: LaneName) -> int:
    lane_priority = {
        "interactive": settings.ORCHESTRATION_LANE_PRIORITY_INTERACTIVE,
        "quality": settings.ORCHESTRATION_LANE_PRIORITY_QUALITY,
        "background": settings.ORCHESTRATION_LANE_PRIORITY_BACKGROUND,
    }[lane]

    quality_delta = {
        "fast": 4,
        "balanced": 0,
        "high": -4,
    }[quality_mode]

    return max(0, lane_priority + quality_delta)


def select_aqe_level(queue_depth: int, infer_stats: Optional[dict[str, Any]] = None) -> AqeLevel:
    if not settings.ORCHESTRATION_AQE_ENABLED:
        return "Q3"

    stats = infer_stats or {}
    waiting_requests = int(stats.get("waiting_requests", 0) or 0)
    avg_wait_time_ms = float(stats.get("avg_wait_time_ms", 0) or 0)
    queue_utilization = float(stats.get("queue_utilization", 0) or 0)

    if (
        queue_depth >= settings.ORCHESTRATION_AQE_Q0_QUEUE_DEPTH
        or waiting_requests >= settings.ORCHESTRATION_AQE_Q0_WAITING_REQUESTS
        or avg_wait_time_ms >= settings.ORCHESTRATION_AQE_Q0_AVG_WAIT_MS
        or queue_utilization >= settings.ORCHESTRATION_AQE_Q0_QUEUE_UTILIZATION
    ):
        return "Q0"

    if (
        queue_depth >= settings.ORCHESTRATION_AQE_Q1_QUEUE_DEPTH
        or waiting_requests >= settings.ORCHESTRATION_AQE_Q1_WAITING_REQUESTS
        or avg_wait_time_ms >= settings.ORCHESTRATION_AQE_Q1_AVG_WAIT_MS
        or queue_utilization >= settings.ORCHESTRATION_AQE_Q1_QUEUE_UTILIZATION
    ):
        return "Q1"

    if (
        queue_depth >= settings.ORCHESTRATION_AQE_Q2_QUEUE_DEPTH
        or waiting_requests >= settings.ORCHESTRATION_AQE_Q2_WAITING_REQUESTS
        or avg_wait_time_ms >= settings.ORCHESTRATION_AQE_Q2_AVG_WAIT_MS
        or queue_utilization >= settings.ORCHESTRATION_AQE_Q2_QUEUE_UTILIZATION
    ):
        return "Q2"

    return "Q3"


@dataclass(slots=True)
class OrchestrationContext:
    db: AsyncSession
    job_id: UUID
    generation_service: Any
    project: Any
    input_data: dict[str, Any]
    quality_mode: UiQualityMode
    target_mode: TargetGenerationMode
    lane: LaneName
    aqe_level: AqeLevel
    queue_depth: int
    infer_stats: Optional[dict[str, Any]] = None
    progress_callback: Optional[ProgressCallback] = None


class GenerationOrchestrator:
    """Runs multi-agent generation stages with cooperative cancellation and AQE."""

    def __init__(self, context: OrchestrationContext) -> None:
        self.context = context
        self.started_at_perf = time.perf_counter()
        self.deadline_perf = (
            self.started_at_perf + settings.ORCHESTRATION_REQUEST_TIME_BUDGET_SECONDS
        )

        self.state: dict[str, Any] = {
            "enabled": settings.ORCHESTRATION_RUNTIME_ENABLED,
            "status": "running",
            "ui_quality_mode": context.quality_mode,
            "target_mode": context.target_mode,
            "lane": context.lane,
            "aqe_level": context.aqe_level,
            "queue_depth": context.queue_depth,
            "infer_stats": context.infer_stats or {},
            "degraded": False,
            "cancelled": False,
            "stages": [],
            "critic": {},
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "budgets": {
                "time_budget_ms": settings.ORCHESTRATION_REQUEST_TIME_BUDGET_SECONDS * 1000,
                "elapsed_ms": 0,
                "remaining_ms": settings.ORCHESTRATION_REQUEST_TIME_BUDGET_SECONDS * 1000,
                "retry_budget": settings.ORCHESTRATION_CRITIC_MAX_ATTEMPTS,
                "retries_used": 0,
            },
        }

    async def run(self) -> dict[str, Any]:
        strategy_output: dict[str, Any] = {}
        design_output: dict[str, Any] = {}
        code_output: dict[str, Any] = {}

        await self._emit_progress()

        try:
            if not settings.ORCHESTRATION_RUNTIME_ENABLED:
                full = await self.context.generation_service.generate_full(
                    self.context.project,
                    self.context.input_data,
                )
                self.state["status"] = "completed"
                return {
                    "strategy": full.get("strategy", {}),
                    "design": full.get("design", {}),
                    "files": full.get("files", {}),
                    "preview_html": full.get("preview_html", ""),
                    "design_style": full.get("design_style", "modern"),
                    "generation_time_ms": full.get("generation_time_ms"),
                    "status": full.get("status", "completed"),
                    "orchestration": self._state_snapshot(),
                }

            if self.context.aqe_level in ("Q3", "Q2"):
                strategy_output = await self._run_stage(
                    stage_id="architect",
                    label="Architect",
                    agent="architect",
                    operation=lambda: self.context.generation_service.generate_strategy(
                        self.context.project,
                        self.context.input_data,
                    ),
                    max_attempts=1,
                )

                coder_bundle = await self._run_stage(
                    stage_id="coder",
                    label="Coder",
                    agent="coder",
                    operation=self._generate_coder_bundle,
                    max_attempts=1,
                )
                design_output = coder_bundle.get("design", {})
                code_output = coder_bundle.get("code", {})

                critic_attempts = (
                    settings.ORCHESTRATION_CRITIC_MAX_ATTEMPTS
                    if self.context.aqe_level == "Q3"
                    else 1
                )
                critic_report, code_output = await self._run_critic_stage(
                    code_output,
                    max_attempts=critic_attempts,
                )
                self.state["critic"] = critic_report
                self.state["degraded"] = not bool(critic_report.get("accepted", False))
            else:
                code_output = await self._run_stage(
                    stage_id="coder",
                    label="Coder",
                    agent="coder",
                    operation=lambda: self.context.generation_service.generate_code(
                        self.context.project,
                        self.context.input_data,
                    ),
                    max_attempts=1,
                )

                strategy_output = {
                    "status": "deferred",
                    "reason": f"aqe_{self.context.aqe_level.lower()}",
                }
                design_output = {
                    "style": code_output.get("design_style", "modern"),
                    "status": "deferred",
                    "reason": f"aqe_{self.context.aqe_level.lower()}",
                }
                self.state["critic"] = {
                    "skipped": True,
                    "reason": f"aqe_{self.context.aqe_level.lower()}",
                    "attempts": 0,
                    "max_attempts": settings.ORCHESTRATION_CRITIC_MAX_ATTEMPTS,
                }
                self.state["degraded"] = True

            self.state["status"] = "completed"
            return {
                "strategy": strategy_output,
                "design": design_output,
                "files": code_output.get("files", {}),
                "preview_html": code_output.get("preview_html", ""),
                "design_style": code_output.get("design_style", "modern"),
                "generation_time_ms": code_output.get("generation_time_ms"),
                "status": code_output.get("status", "completed"),
                "orchestration": self._state_snapshot(),
            }

        except OrchestrationCancelledError:
            self.state["status"] = "cancelled"
            self.state["cancelled"] = True
            raise
        except Exception as exc:
            self.state["status"] = "failed"
            self.state["error"] = str(exc)
            raise
        finally:
            self._refresh_budget()
            self.state["completed_at"] = datetime.now(timezone.utc).isoformat()
            await self._emit_progress()

    async def _generate_coder_bundle(self) -> dict[str, Any]:
        await self._assert_not_cancelled()
        design_output = await self.context.generation_service.generate_design(
            self.context.project,
            self.context.input_data,
        )

        await self._assert_not_cancelled()
        code_output = await self.context.generation_service.generate_code(
            self.context.project,
            self.context.input_data,
        )

        return {
            "design": design_output,
            "code": code_output,
        }

    async def _run_critic_stage(
        self,
        code_output: dict[str, Any],
        max_attempts: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        stage: dict[str, Any] = {
            "id": "critic",
            "label": "Critic",
            "agent": "critic",
            "status": "running",
            "attempt": 0,
            "max_attempts": max_attempts,
            "duration_ms": None,
            "detail": "Running quality checks",
            "logs": [],
        }
        self.state["stages"].append(stage)
        stage_started_at = time.perf_counter()
        await self._emit_progress()

        for attempt in range(1, max_attempts + 1):
            await self._assert_not_cancelled()
            self._assert_budget_remaining()

            stage["attempt"] = attempt
            stage["logs"].append(f"Attempt {attempt}: evaluating output quality")
            issues = self._evaluate_critic_issues(code_output)

            if not issues:
                stage["status"] = "completed"
                stage["detail"] = "Quality checks passed"
                stage["duration_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
                await self._emit_progress()
                return (
                    {
                        "accepted": True,
                        "issues": [],
                        "attempts": attempt,
                        "max_attempts": max_attempts,
                    },
                    code_output,
                )

            stage["logs"].append(
                f"Attempt {attempt}: found {len(issues)} issue(s): {', '.join(issues)}"
            )

            if attempt >= max_attempts:
                stage["status"] = "failed"
                stage["detail"] = "Critic max attempts exhausted"
                stage["duration_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
                self.state["budgets"]["retries_used"] = attempt
                await self._emit_progress()

                if settings.ORCHESTRATION_CRITIC_STRICT_FAIL:
                    raise RuntimeError("Critic exhausted retries and strict-fail is enabled")

                return (
                    {
                        "accepted": False,
                        "issues": issues,
                        "attempts": attempt,
                        "max_attempts": max_attempts,
                    },
                    code_output,
                )

            self.state["budgets"]["retries_used"] = attempt
            stage["detail"] = "Issues found, retrying coder stage"
            await self._emit_progress()

            await self._assert_not_cancelled()
            self._assert_budget_remaining()
            timeout_seconds = self._compute_stage_timeout_seconds()
            code_output = await asyncio.wait_for(
                self.context.generation_service.generate_code(
                    self.context.project,
                    self.context.input_data,
                ),
                timeout=timeout_seconds,
            )

        # Guard path; loop always returns.
        stage["status"] = "failed"
        stage["detail"] = "Critic aborted unexpectedly"
        stage["duration_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
        await self._emit_progress()
        return (
            {
                "accepted": False,
                "issues": ["critic_aborted"],
                "attempts": max_attempts,
                "max_attempts": max_attempts,
            },
            code_output,
        )

    async def _run_stage(
        self,
        stage_id: str,
        label: str,
        agent: str,
        operation: Callable[[], Awaitable[Any]],
        max_attempts: int,
    ) -> Any:
        stage: dict[str, Any] = {
            "id": stage_id,
            "label": label,
            "agent": agent,
            "status": "pending",
            "attempt": 0,
            "max_attempts": max_attempts,
            "duration_ms": None,
            "detail": "Pending",
            "logs": [],
        }
        self.state["stages"].append(stage)
        await self._emit_progress()

        for attempt in range(1, max_attempts + 1):
            await self._assert_not_cancelled()
            self._assert_budget_remaining()

            stage["status"] = "running"
            stage["attempt"] = attempt
            stage["detail"] = f"Attempt {attempt} running"
            stage["logs"].append(f"Attempt {attempt}: started")
            await self._emit_progress()

            stage_started_at = time.perf_counter()
            timeout_seconds = self._compute_stage_timeout_seconds()

            try:
                value = await asyncio.wait_for(operation(), timeout=timeout_seconds)
                stage["status"] = "completed"
                stage["detail"] = "Completed"
                stage["duration_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
                stage["logs"].append("Completed successfully")
                await self._emit_progress()
                return value
            except OrchestrationCancelledError:
                stage["status"] = "failed"
                stage["detail"] = "Cancelled"
                stage["duration_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
                stage["logs"].append("Cancelled by user")
                await self._emit_progress()
                raise
            except asyncio.TimeoutError as exc:
                stage["status"] = "failed"
                stage["detail"] = "Timed out"
                stage["duration_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
                stage["logs"].append(
                    f"Timed out after {timeout_seconds}s (attempt {attempt})"
                )
                await self._emit_progress()
                if attempt >= max_attempts:
                    raise RuntimeError(
                        f"Stage '{stage_id}' timed out after {attempt} attempt(s)"
                    ) from exc
            except Exception as exc:
                stage["status"] = "failed"
                stage["detail"] = "Failed"
                stage["duration_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
                stage["logs"].append(f"Attempt {attempt} failed: {exc}")
                await self._emit_progress()
                if attempt >= max_attempts:
                    raise RuntimeError(
                        f"Stage '{stage_id}' failed after {attempt} attempt(s): {exc}"
                    ) from exc

        raise RuntimeError(f"Stage '{stage_id}' exited unexpectedly")

    def _evaluate_critic_issues(self, code_output: dict[str, Any]) -> list[str]:
        issues: list[str] = []

        files = code_output.get("files")
        preview_html = code_output.get("preview_html")

        if not isinstance(files, dict) or len(files) == 0:
            issues.append("missing_files")
        else:
            has_index = "index.html" in files or any(
                isinstance(path, str) and path.endswith("/index.html") for path in files.keys()
            )
            if not has_index:
                issues.append("missing_index_html")

        if not isinstance(preview_html, str) or not preview_html.strip():
            issues.append("missing_preview_html")

        return issues

    def _compute_stage_timeout_seconds(self) -> int:
        remaining = int(self.deadline_perf - time.perf_counter())
        if remaining <= 0:
            raise OrchestrationBudgetExceededError("Generation budget exhausted")
        return max(1, min(settings.ORCHESTRATION_STAGE_TIMEOUT_SECONDS, remaining))

    def _assert_budget_remaining(self) -> None:
        if time.perf_counter() >= self.deadline_perf:
            raise OrchestrationBudgetExceededError("Generation budget exhausted")

    async def _assert_not_cancelled(self) -> None:
        result = await self.context.db.execute(
            select(Job.status).where(Job.id == self.context.job_id)
        )
        status_value = result.scalar_one_or_none()

        normalized_status = (
            status_value.value if isinstance(status_value, JobStatus) else str(status_value)
        )
        if normalized_status == JobStatus.CANCELLED.value:
            raise OrchestrationCancelledError("Job was cancelled")

    async def _emit_progress(self) -> None:
        self._refresh_budget()
        if self.context.progress_callback:
            await self.context.progress_callback(self._state_snapshot())

    def _refresh_budget(self) -> None:
        elapsed_ms = int((time.perf_counter() - self.started_at_perf) * 1000)
        remaining_ms = max(
            0,
            settings.ORCHESTRATION_REQUEST_TIME_BUDGET_SECONDS * 1000 - elapsed_ms,
        )
        self.state["budgets"]["elapsed_ms"] = elapsed_ms
        self.state["budgets"]["remaining_ms"] = remaining_ms

    def _state_snapshot(self) -> dict[str, Any]:
        return deepcopy(self.state)
