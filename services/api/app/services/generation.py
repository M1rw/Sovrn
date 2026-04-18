"""Production generation service built on the active agent pipeline.

This service is the canonical bridge for website generation. It uses the
active strategist, designer, and engineer agents, while preserving the same
output shape used by orchestration and worker flows.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import time
from typing import Any

from app.core.config import settings
from app.agents.common import DesignSystem, GeneratedSite, SiteStrategy
from app.agents.designer import designer_agent
from app.agents.engineer import engineer_agent
from app.agents.strategist import strategist_agent


_production_engine: "_ProductionWebsiteEngine | None" = None
_starter_template_cache: dict[str, dict[str, Any]] = {}

_SUPPORTED_STYLES = {"modern", "minimal", "bold", "elegant", "playful", "corporate", "dark", "light"}


def _normalize_style(value: Any) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _SUPPORTED_STYLES:
            return normalized
    return "modern"


def _project_name(project: Any) -> str:
    name = getattr(project, "name", "") or ""
    return name.strip() or "SOVRN Site"


def _project_locale(project: Any, input_data: dict[str, Any]) -> str:
    locale = input_data.get("locale") or getattr(project, "locale", "en") or "en"
    return str(locale)


def _project_industry(project: Any, input_data: dict[str, Any]) -> str | None:
    industry = input_data.get("industry") or getattr(project, "industry", None)
    return str(industry) if industry else None


def _project_business_type(project: Any, input_data: dict[str, Any]) -> str | None:
    business_type = input_data.get("business_type") or getattr(project, "business_type", None)
    return str(business_type) if business_type else None


def _project_target_audience(project: Any, input_data: dict[str, Any]) -> Any:
    return input_data.get("target_audience") or getattr(project, "target_audience", None)


def _project_goals(project: Any, input_data: dict[str, Any]) -> Any:
    return input_data.get("goals") or getattr(project, "goals", None)


def _project_brief(project: Any, input_data: dict[str, Any]) -> str:
    brief = input_data.get("brief") or getattr(project, "brief", "") or "Build a website"
    return str(brief)


def _project_style(input_data: dict[str, Any]) -> str:
    return _normalize_style(input_data.get("style") or input_data.get("design_style"))


def _truncate_utf8_bytes(content: str, max_bytes: int) -> str:
    encoded = content.encode("utf-8")
    if len(encoded) <= max_bytes:
        return content
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _build_starter_template(style: str) -> dict[str, Any]:
    palette = {
        "modern": ("#2563eb", "#0f172a"),
        "minimal": ("#334155", "#111827"),
        "bold": ("#dc2626", "#111827"),
        "elegant": ("#7c3aed", "#1f2937"),
        "playful": ("#ea580c", "#0f172a"),
        "corporate": ("#0ea5e9", "#0f172a"),
        "dark": ("#38bdf8", "#e2e8f0"),
        "light": ("#2563eb", "#0f172a"),
    }
    accent, text_color = palette.get(style, palette["modern"])
    bg_color = "#0b1220" if style == "dark" else "#f8fafc"

    html = """<!doctype html>
<html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>SOVRN Starter</title>
        <link rel=\"stylesheet\" href=\"styles.css\" />
    </head>
    <body>
        <main class=\"shell\">
            <span class=\"badge\">SOVRN starter template</span>
            <h1>Preview runtime is ready.</h1>
            <p>This is a cached starter template while the full generation pipeline warms up.</p>
            <button type=\"button\">Continue editing</button>
        </main>
        <script src=\"script.js\"></script>
    </body>
</html>
"""

    css = f"""* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: {bg_color}; color: {text_color}; }}
.shell {{ min-height: 100vh; display: grid; gap: 1rem; place-content: center; padding: 2.5rem; text-align: center; }}
.badge {{ display: inline-block; margin: 0 auto; padding: 0.4rem 0.75rem; border-radius: 9999px; background: {accent}; color: white; font-size: 0.8rem; font-weight: 600; }}
h1 {{ margin: 0; font-size: clamp(1.8rem, 4vw, 2.8rem); }}
p {{ margin: 0 auto; max-width: 42rem; color: rgba(30, 41, 59, 0.85); }}
button {{ margin: 0 auto; border: 0; border-radius: 0.75rem; padding: 0.8rem 1.15rem; background: {accent}; color: white; font-weight: 600; cursor: pointer; }}
"""

    js = """(function () {
    const btn = document.querySelector('button');
    if (!btn) return;
    btn.addEventListener('click', function () {
        btn.textContent = 'Starter loaded';
        btn.disabled = true;
    });
})();
"""

    preview_html = html.replace(
        '<link rel="stylesheet" href="styles.css" />',
        f"<style>{css}</style>",
    ).replace(
        '<script src="script.js"></script>',
        f"<script>{js}</script>",
    )

    return {
        "files": {
            "index.html": html,
            "styles.css": css,
            "script.js": js,
        },
        "preview_html": preview_html,
        "design_style": style,
    }


class _ProductionWebsiteEngine:
    """Agent-backed code generator used by the production generation service."""

    async def generate(self, prompt: str, *, project_name: str, design_style: str) -> dict[str, Any]:
        strategy = strategist_agent.analyze(
            brief=prompt,
            additional_context={
                "brand_voice": "clear, confident, helpful",
                "cta": "Get started",
                "design_style": design_style,
            },
        )
        design = await designer_agent.design(strategy)
        site: GeneratedSite = await asyncio.to_thread(
            engineer_agent.generate,
            strategy,
            design,
            project_name,
        )

        files = {artifact.path: artifact.content for artifact in site.files}
        preview_html = files.get("app/page.tsx") or next(iter(files.values()), "")

        return {
            "success": bool(files),
            "files": files,
            "preview_html": preview_html,
            "design_style": design.style_theme,
            "generation_time_ms": 0,
            "strategy": asdict(strategy),
            "design": asdict(design),
            "dependencies": site.dependencies,
            "tests": site.tests,
        }


class GenerationService:
    """Minimal generation pipeline facade used by API endpoints."""

    def __init__(self, db: Any, inference_url: str | None = None) -> None:
        self.db = db
        self.inference_url = inference_url

    async def _get_advanced_engine(self) -> _ProductionWebsiteEngine:
        global _production_engine

        if _production_engine is None:
            _production_engine = _ProductionWebsiteEngine()

        return _production_engine

    def _build_prompt(self, project: Any, input_data: dict[str, Any]) -> str:
        brief = _project_brief(project, input_data)
        locale = _project_locale(project, input_data)
        industry = _project_industry(project, input_data)
        business_type = _project_business_type(project, input_data)
        target_audience = _project_target_audience(project, input_data)
        goals = _project_goals(project, input_data)
        style = _project_style(input_data)

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

    def _build_strategy_output(self, project: Any, input_data: dict[str, Any], prompt: str) -> dict[str, Any]:
        strategy: SiteStrategy = strategist_agent.analyze(
            brief=_project_brief(project, input_data),
            locale=_project_locale(project, input_data),
            industry=_project_industry(project, input_data),
            additional_context={
                "business_model": _project_business_type(project, input_data),
                "target_audience": _project_target_audience(project, input_data),
                "goals": _project_goals(project, input_data),
                "brand_voice": input_data.get("brand_voice", "clear, confident, helpful"),
                "cta": input_data.get("cta", "Get started"),
                "design_style": _project_style(input_data),
            },
        )

        strategy_output = asdict(strategy)
        strategy_output.update(
            {
                "project_id": str(getattr(project, "id", "unknown")),
                "brief": _project_brief(project, input_data),
                "locale": _project_locale(project, input_data),
                "industry": _project_industry(project, input_data),
                "business_type": _project_business_type(project, input_data),
                "target_audience": _project_target_audience(project, input_data),
                "goals": _project_goals(project, input_data),
                "prompt": prompt,
                "design_style": _project_style(input_data),
                "status": "generated",
            }
        )
        return strategy_output

    async def _build_design_output(self, project: Any, input_data: dict[str, Any], prompt: str) -> dict[str, Any]:
        strategy: SiteStrategy = strategist_agent.analyze(
            brief=_project_brief(project, input_data),
            locale=_project_locale(project, input_data),
            industry=_project_industry(project, input_data),
            additional_context={
                "business_model": _project_business_type(project, input_data),
                "target_audience": _project_target_audience(project, input_data),
                "goals": _project_goals(project, input_data),
                "brand_voice": input_data.get("brand_voice", "clear, confident, helpful"),
                "cta": input_data.get("cta", "Get started"),
                "design_style": _project_style(input_data),
            },
        )
        design: DesignSystem = await designer_agent.design(
            strategy,
            locale=_project_locale(project, input_data),
            country_code=str(input_data.get("country_code", "US")),
            brand_guidelines=input_data.get("brand_guidelines"),
        )

        design_output = asdict(design)
        design_output.update(
            {
                "project_id": str(getattr(project, "id", "unknown")),
                "prompt": prompt,
                "style": design.style_theme,
                "design_style": design.style_theme,
                "locale": _project_locale(project, input_data),
                "responsive": True,
                "status": "generated",
            }
        )
        return design_output

    def _apply_preview_file_budgets(self, raw_files: Any) -> tuple[dict[str, str], dict[str, int]]:
        if not isinstance(raw_files, dict):
            return {}, {
                "max_files": settings.PREVIEW_BUILD_MAX_FILES,
                "max_total_bytes": settings.PREVIEW_BUILD_MAX_TOTAL_BYTES,
                "max_file_bytes": settings.PREVIEW_BUILD_MAX_FILE_BYTES,
                "total_bytes": 0,
                "truncated_files": 0,
                "dropped_files": 0,
            }

        max_files = settings.PREVIEW_BUILD_MAX_FILES
        max_total_bytes = settings.PREVIEW_BUILD_MAX_TOTAL_BYTES
        max_file_bytes = settings.PREVIEW_BUILD_MAX_FILE_BYTES

        normalized_files: dict[str, str] = {}
        total_bytes = 0
        truncated_files = 0
        dropped_files = 0

        for path, raw_content in raw_files.items():
            if not isinstance(path, str) or not path.strip():
                continue

            if len(normalized_files) >= max_files:
                dropped_files += 1
                continue

            content = raw_content if isinstance(raw_content, str) else ""
            truncated_content = _truncate_utf8_bytes(content, max_file_bytes)
            if truncated_content != content:
                truncated_files += 1

            remaining_bytes = max_total_bytes - total_bytes
            if remaining_bytes <= 0:
                dropped_files += 1
                continue

            bounded_content = _truncate_utf8_bytes(truncated_content, remaining_bytes)
            if bounded_content != truncated_content:
                truncated_files += 1

            bounded_size = len(bounded_content.encode("utf-8"))
            total_bytes += bounded_size
            normalized_files[path] = bounded_content

        return normalized_files, {
            "max_files": max_files,
            "max_total_bytes": max_total_bytes,
            "max_file_bytes": max_file_bytes,
            "total_bytes": total_bytes,
            "truncated_files": truncated_files,
            "dropped_files": dropped_files,
        }

    def _get_cached_starter_template(self, style_value: Any) -> dict[str, Any]:
        style = _normalize_style(style_value)
        cached = _starter_template_cache.get(style)
        if cached is not None:
            return cached

        template = _build_starter_template(style)
        _starter_template_cache[style] = template
        return template

    async def generate_strategy(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(project, input_data)
        return self._build_strategy_output(project, input_data, prompt)

    async def generate_design(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(project, input_data)
        return await self._build_design_output(project, input_data, prompt)

    async def generate_code(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        start_time = time.time()
        prompt = self._build_prompt(project, input_data)
        requested_style = _project_style(input_data)
        advanced = await self._get_advanced_engine()

        try:
            result = await asyncio.wait_for(
                advanced.generate(
                    prompt,
                    project_name=_project_name(project),
                    design_style=requested_style,
                ),
                timeout=settings.PREVIEW_BUILD_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            template = self._get_cached_starter_template(requested_style)
            files, build_budget = self._apply_preview_file_budgets(template.get("files", {}))
            preview_html = _truncate_utf8_bytes(
                template.get("preview_html", ""),
                settings.PREVIEW_BUILD_MAX_TOTAL_BYTES,
            )
            return {
                "stage": "code",
                "project_id": str(getattr(project, "id", "unknown")),
                "brief": input_data.get("brief", ""),
                "files": files,
                "preview_html": preview_html,
                "design_style": template.get("design_style", _normalize_style(requested_style)),
                "status": "completed_fallback",
                "error": f"Preview build timed out after {settings.PREVIEW_BUILD_TIMEOUT_SECONDS}s",
                "fallback_reason": "timeout",
                "generation_time_ms": int((time.time() - start_time) * 1000),
                "build_budget": {
                    "timeout_seconds": settings.PREVIEW_BUILD_TIMEOUT_SECONDS,
                    **build_budget,
                },
            }

        result_is_dict = isinstance(result, dict)
        result_success = bool(result.get("success", False)) if result_is_dict else False
        raw_files = result.get("files", {}) if result_is_dict else {}
        raw_preview_html = result.get("preview_html", "") if result_is_dict else ""

        should_use_fallback = (
            not result_success
            or not isinstance(raw_files, dict)
            or len(raw_files) == 0
            or not isinstance(raw_preview_html, str)
            or not raw_preview_html.strip()
        )

        fallback_reason: str | None = None
        if should_use_fallback:
            template = self._get_cached_starter_template(
                result.get("design_style", requested_style) if result_is_dict else requested_style,
            )
            files, build_budget = self._apply_preview_file_budgets(template.get("files", {}))
            preview_html = _truncate_utf8_bytes(
                template.get("preview_html", ""),
                settings.PREVIEW_BUILD_MAX_TOTAL_BYTES,
            )
            design_style = template.get("design_style", _normalize_style(requested_style))
            fallback_reason = "generation_failed"
            status_value = "completed_fallback"
        else:
            files, build_budget = self._apply_preview_file_budgets(raw_files)
            preview_html = _truncate_utf8_bytes(raw_preview_html, settings.PREVIEW_BUILD_MAX_TOTAL_BYTES)
            design_style = result.get("design_style", requested_style)
            status_value = "completed"

        response = {
            "stage": "code",
            "project_id": str(getattr(project, "id", "unknown")),
            "brief": input_data.get("brief", ""),
            "files": files,
            "preview_html": preview_html,
            "design_style": design_style,
            "status": status_value,
            "generation_time_ms": (
                result.get("generation_time_ms", int((time.time() - start_time) * 1000))
                if isinstance(result, dict)
                else int((time.time() - start_time) * 1000)
            ),
            "build_budget": {
                "timeout_seconds": settings.PREVIEW_BUILD_TIMEOUT_SECONDS,
                **build_budget,
            },
        }

        if fallback_reason:
            response["fallback_reason"] = fallback_reason

        return response

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
