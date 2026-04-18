"""HTTP-backed inference client used by API services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import httpx

from app.core.config import settings


@dataclass(slots=True)
class InferenceClient:
    """Small async client for the local inference service."""

    base_url: str | None = settings.INFERENCE_URL
    timeout_seconds: int = settings.INFERENCE_TIMEOUT
    max_retries: int = 2

    def _resolve_base_url(self) -> str:
        if not self.base_url:
            raise RuntimeError("Inference base URL is not configured")
        return self.base_url.rstrip("/")

    async def health(self) -> dict[str, Any]:
        """Check inference service health endpoint."""
        url = f"{self._resolve_base_url()}/health"
        last_error = "unknown"
        for _ in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise RuntimeError("Inference health response is not a JSON object")
                    return payload
            except httpx.HTTPError as exc:
                last_error = str(exc)

        return {
            "status": "unavailable",
            "base_url": self.base_url,
            "error": last_error,
        }

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        stop: Iterable[str] | None = None,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate text using OpenAI-compatible completion endpoint."""
        payload: dict[str, Any] = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        if stop is not None:
            payload["stop"] = list(stop)
        if json_schema is not None:
            payload["json_schema"] = json_schema

        response = await self._post_json("/v1/completions", payload)
        return response

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "default",
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        stop: Iterable[str] | None = None,
        json_schema: dict[str, Any] | None = None,
        grounding: str | None = None,
    ) -> dict[str, Any]:
        """Generate chat output using OpenAI-compatible chat endpoint."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        if stop is not None:
            payload["stop"] = list(stop)
        if json_schema is not None:
            payload["json_schema"] = json_schema
        if grounding:
            payload["grounding"] = grounding

        response = await self._post_json("/v1/chat/completions", payload)
        return response

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._resolve_base_url()}{path}"
        timeout = httpx.Timeout(float(self.timeout_seconds))
        last_error: Exception | None = None

        for _ in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        raise RuntimeError(f"Inference response at {path} is not a JSON object")
                    return data
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise RuntimeError(f"Inference request to {path} failed after retries") from last_error

        # HTTP status errors are deterministic and should be surfaced immediately.
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError(f"Inference response at {path} is not a JSON object")
            return data


inference_client = InferenceClient()
