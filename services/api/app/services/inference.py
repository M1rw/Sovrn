"""Inference client compatibility shim."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class InferenceClient:
    """Minimal inference client used by the API at startup."""

    base_url: str | None = None

    async def health(self) -> dict[str, Any]:
        return {"status": "unavailable", "base_url": self.base_url}

    async def generate(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "unavailable", "args": args, "kwargs": kwargs}


inference_client = InferenceClient()
