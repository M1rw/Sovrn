from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic import ValidationError
import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://sovrn:devpassword@localhost:5432/sovrn")

from app.api.v1.endpoints import projects  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.schemas import GenerateSiteRequest  # noqa: E402
from app.services.orchestration import (  # noqa: E402
    map_ui_quality_to_target_mode,
    normalize_ui_quality_mode,
    resolve_generation_lane,
    resolve_generation_priority,
    select_aqe_level,
)


def test_generate_site_request_quality_mode_defaults_to_balanced() -> None:
    payload = GenerateSiteRequest.model_validate(
        {
            "brief": "Build a conversion-focused landing page for a SaaS product",
        }
    )

    assert payload.quality_mode == "balanced"


def test_generate_site_request_rejects_unknown_quality_mode() -> None:
    with pytest.raises(ValidationError):
        GenerateSiteRequest.model_validate(
            {
                "brief": "Build a conversion-focused landing page for a SaaS product",
                "quality_mode": "ultra",
            }
        )


def test_quality_mode_helpers_map_high_to_quality_profile() -> None:
    quality_mode = normalize_ui_quality_mode("high")

    assert quality_mode == "high"
    assert map_ui_quality_to_target_mode(quality_mode) == "quality"
    assert resolve_generation_lane(quality_mode) == "interactive"


def test_generation_priority_favors_fast_over_high_for_same_lane() -> None:
    lane = "interactive"

    fast_priority = resolve_generation_priority("fast", lane)
    balanced_priority = resolve_generation_priority("balanced", lane)
    high_priority = resolve_generation_priority("high", lane)

    assert fast_priority >= balanced_priority >= high_priority


def test_projects_orchestration_metadata_builder_returns_expected_contract() -> None:
    metadata, priority = projects._build_generation_orchestration_metadata("high")

    assert metadata["enabled"] == settings.ORCHESTRATION_RUNTIME_ENABLED
    assert metadata["quality_mode"] == "high"
    assert metadata["target_mode"] == "quality"
    assert metadata["lane"] == "interactive"
    assert priority == resolve_generation_priority("high", "interactive")


def test_aqe_level_selection_respects_queue_depth_thresholds() -> None:
    assert select_aqe_level(settings.ORCHESTRATION_AQE_Q0_QUEUE_DEPTH, {}) == "Q0"
    assert select_aqe_level(settings.ORCHESTRATION_AQE_Q1_QUEUE_DEPTH, {}) in ("Q1", "Q0")
    assert select_aqe_level(settings.ORCHESTRATION_AQE_Q2_QUEUE_DEPTH, {}) in ("Q2", "Q1", "Q0")


def test_aqe_level_selection_uses_inference_wait_signals() -> None:
    level = select_aqe_level(
        0,
        {
            "waiting_requests": settings.ORCHESTRATION_AQE_Q1_WAITING_REQUESTS,
            "avg_wait_time_ms": settings.ORCHESTRATION_AQE_Q1_AVG_WAIT_MS,
            "queue_utilization": settings.ORCHESTRATION_AQE_Q1_QUEUE_UTILIZATION,
        },
    )

    assert level in ("Q1", "Q0")
