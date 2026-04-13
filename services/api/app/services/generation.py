"""Generation service compatibility shim.

This service is the canonical job processor bridge for website generation.
It intentionally reuses the existing local website engines instead of returning
stubbed outputs so the worker path produces real artifacts.
"""

from __future__ import annotations

import time
from typing import Any

from app.lib.ai.advanced_mml import AdvancedMMLEngine
from app.lib.ai.mml_engine import get_mml_engine, WebsiteStyle


_advanced_engine: AdvancedMMLEngine | None = None


def _coerce_style(value: Any) -> WebsiteStyle:
    try:
        if isinstance(value, str):
            return WebsiteStyle(value.lower())
    except Exception:
        pass
    return WebsiteStyle.MODERN


class GenerationService:
    """Minimal generation pipeline facade used by API endpoints."""

    def __init__(self, db: Any, inference_url: str | None = None) -> None:
        self.db = db
        self.inference_url = inference_url

    async def _get_advanced_engine(self) -> AdvancedMMLEngine:
        global _advanced_engine

        if _advanced_engine is None:
            _advanced_engine = AdvancedMMLEngine()
            await _advanced_engine.load()

        return _advanced_engine

    def _build_prompt(self, project: Any, input_data: dict[str, Any]) -> str:
        brief = input_data.get("brief") or getattr(project, "brief", "") or "Build a website"
        locale = input_data.get("locale") or getattr(project, "locale", "en")
        industry = input_data.get("industry") or getattr(project, "industry", None)
        business_type = input_data.get("business_type") or getattr(project, "business_type", None)
        target_audience = input_data.get("target_audience") or getattr(project, "target_audience", None)
        goals = input_data.get("goals") or getattr(project, "goals", None)
        style = input_data.get("style") or input_data.get("design_style") or "modern"

        parts = [brief, f"Locale: {locale}", f"Style: {style}"]
        if industry:
            parts.append(f"Industry: {industry}")
        if business_type:
            parts.append(f"Business type: {business_type}")
        if target_audience:
            parts.append(f"Target audience: {target_audience}")
        if goals:
            parts.append(f"Goals: {goals}")

        return "\n".join(str(part) for part in parts if part)

    def _build_strategy_output(self, project: Any, input_data: dict[str, Any], prompt: str, design_style: str) -> dict[str, Any]:
        brief = input_data.get("brief") or getattr(project, "brief", "") or ""
        return {
            "project_id": str(getattr(project, "id", "unknown")),
            "brief": brief,
            "locale": input_data.get("locale") or getattr(project, "locale", "en"),
            "industry": input_data.get("industry") or getattr(project, "industry", None),
            "business_type": input_data.get("business_type") or getattr(project, "business_type", None),
            "target_audience": input_data.get("target_audience") or getattr(project, "target_audience", None),
            "goals": input_data.get("goals") or getattr(project, "goals", None),
            "prompt": prompt,
            "design_style": design_style,
            "status": "generated",
        }

    def _build_design_output(self, input_data: dict[str, Any], design_style: str) -> dict[str, Any]:
        return {
            "style": design_style,
            "responsive": True,
            "locale": input_data.get("locale") or "en",
            "status": "generated",
        }

    async def generate_strategy(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(project, input_data)
        advanced = await self._get_advanced_engine()

        analysis = advanced._analyze_prompt(prompt) if hasattr(advanced, "_analyze_prompt") else None
        design_style = analysis.style if analysis else _coerce_style(input_data.get("style")).value

        return self._build_strategy_output(project, input_data, prompt, design_style)

    async def generate_design(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(project, input_data)
        advanced = await self._get_advanced_engine()

        analysis = advanced._analyze_prompt(prompt) if hasattr(advanced, "_analyze_prompt") else None
        design_style = analysis.style if analysis else _coerce_style(input_data.get("style")).value

        return self._build_design_output(input_data, design_style)

    async def generate_code(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(project, input_data)
        advanced = await self._get_advanced_engine()

        result = await advanced.generate(prompt)
        files = result.get("files", {}) if isinstance(result, dict) else {}
        preview_html = result.get("preview_html", "") if isinstance(result, dict) else ""
        design_style = result.get("design_style", input_data.get("style", "modern")) if isinstance(result, dict) else input_data.get("style", "modern")

        return {
            "stage": "code",
            "project_id": str(getattr(project, "id", "unknown")),
            "brief": input_data.get("brief", ""),
            "files": files,
            "preview_html": preview_html,
            "design_style": design_style,
            "status": "completed" if result.get("success", False) else "failed",
            "generation_time_ms": result.get("generation_time_ms", 0),
        }

    async def generate_full(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        start_time = time.time()

        strategy = await self.generate_strategy(project, input_data)
        design = await self.generate_design(project, input_data)
        code = await self.generate_code(project, input_data)

        return {
            "strategy": strategy,
            "design": design,
            "files": code.get("files", {}),
            "preview_html": code.get("preview_html", ""),
            "design_style": code.get("design_style", "modern"),
            "generation_time_ms": code.get("generation_time_ms", int((time.time() - start_time) * 1000)),
            "status": code.get("status", "completed"),
        }
