"""Generation service compatibility shim."""

from __future__ import annotations

from typing import Any


class GenerationService:
    """Minimal generation pipeline facade used by API endpoints."""

    def __init__(self, db: Any, inference_url: str | None = None) -> None:
        self.db = db
        self.inference_url = inference_url

    async def generate_strategy(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        return self._result("strategy", project, input_data)

    async def generate_design(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        return self._result("design", project, input_data)

    async def generate_code(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        return self._result("code", project, input_data)

    async def generate_full(self, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        strategy = await self.generate_strategy(project, input_data)
        design = await self.generate_design(project, input_data)
        code = await self.generate_code(project, input_data)
        return {
            "strategy": strategy,
            "design": design,
            "files": code.get("files", {}),
            "status": "stubbed",
        }

    def _result(self, stage: str, project: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        project_id = str(getattr(project, "id", "unknown"))
        brief = input_data.get("brief", "") if isinstance(input_data, dict) else ""
        return {
            "stage": stage,
            "project_id": project_id,
            "brief": brief,
            "files": {},
            "status": "stubbed",
        }
