# =============================================================================
# SOVRN Inference Service - Inference Engine
# =============================================================================
"""
Handles actual inference requests using llama.cpp
"""

import asyncio
import json
import re
import time
from typing import AsyncIterator, Dict, List, Optional, Tuple
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

from config import settings
from model_manager import model_manager

logger = structlog.get_logger()


# =============================================================================
# Request/Response Models (OpenAI-compatible)
# =============================================================================

class Message(BaseModel):
    """Chat message."""
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request (OpenAI-compatible)."""
    model: str = "default"
    messages: List[Message]
    json_schema: Optional[Dict] = None
    grounding: Optional[str] = None
    temperature: float = Field(default=settings.DEFAULT_TEMPERATURE, ge=0, le=2)
    top_p: float = Field(default=settings.DEFAULT_TOP_P, ge=0, le=1)
    top_k: int = Field(default=settings.DEFAULT_TOP_K, ge=1)
    max_tokens: int = Field(default=512, ge=1, le=settings.MAX_TOKENS)
    stream: bool = False
    stop: Optional[List[str]] = None


class CompletionRequest(BaseModel):
    """Text completion request."""
    prompt: str
    model: Optional[str] = "default"
    json_schema: Optional[Dict] = None
    temperature: float = Field(default=settings.DEFAULT_TEMPERATURE, ge=0, le=2)
    top_p: float = Field(default=settings.DEFAULT_TOP_P, ge=0, le=1)
    max_tokens: int = Field(default=512, ge=1, le=settings.MAX_TOKENS)
    stream: bool = False
    stop: Optional[List[str]] = None


class CompletionChoice(BaseModel):
    """Completion choice."""
    text: str
    index: int
    finish_reason: str


class CompletionUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class CompletionResponse(BaseModel):
    """Completion response."""
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: CompletionUsage


class ChatCompletionChoice(BaseModel):
    """Chat completion choice."""
    index: int
    message: Message
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: CompletionUsage


# =============================================================================
# Inference Engine
# =============================================================================

class InferenceEngine:
    """Handles inference requests with queueing and concurrency control."""
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=settings.QUEUE_SIZE)
        self.started_at = time.time()
        self.active_requests = 0
        self.waiting_requests = 0
        self.max_observed_concurrency = 0
        self.total_requests = 0
        self.total_tokens_generated = 0
        self.total_wait_time_ms = 0.0
        self.wait_events = 0
        self._response_cache: Dict[str, Tuple[float, Dict]] = {}

    async def _wait_for_capacity(self, request_id: str, endpoint: str) -> float:
        """Wait for a free inference slot and return wait time in ms."""
        if self.active_requests < settings.MAX_CONCURRENT_REQUESTS:
            return 0.0

        wait_started_at = time.perf_counter()
        self.waiting_requests += 1
        try:
            while self.active_requests >= settings.MAX_CONCURRENT_REQUESTS:
                await asyncio.sleep(0.05)
        finally:
            self.waiting_requests = max(0, self.waiting_requests - 1)

        wait_ms = (time.perf_counter() - wait_started_at) * 1000
        self.total_wait_time_ms += wait_ms
        self.wait_events += 1
        logger.info(
            "inference_wait_for_capacity",
            request_id=request_id,
            endpoint=endpoint,
            wait_ms=round(wait_ms, 2),
            active_requests=self.active_requests,
            waiting_requests=self.waiting_requests,
        )
        return wait_ms
        
    async def chat_completion(
        self,
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse | AsyncIterator[str]:
        """
        Generate chat completion.
        
        Args:
            request: Chat completion request
            
        Returns:
            Complete response or streaming iterator
        """
        self.total_requests += 1
        request_id = f"chatcmpl-{uuid4().hex[:24]}"
        
        logger.info(
            "chat_completion_start",
            request_id=request_id,
            messages_count=len(request.messages),
            max_tokens=request.max_tokens,
            stream=request.stream
        )
        
        model_name = self._select_model_name(request.model, request.messages)
        target_model_path = self._resolve_model_path(model_name)
        model = await model_manager.load_model(model_path=target_model_path)
        
        # Inject grounding context if provided
        messages = list(request.messages)
        if request.grounding:
            messages = [Message(role="system", content=f"Grounding context:\n{request.grounding}")] + messages

        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)

        cache_key = self._cache_key(model_name, prompt, request)
        if settings.ENABLE_RESPONSE_CACHE and not request.stream:
            cached = self._response_cache.get(cache_key)
            if cached:
                logger.info("response_cache_hit", request_id=request_id, model=model_name)
                return cached[1]

        wait_ms = await self._wait_for_capacity(request_id, "chat_completion")
        
        self.active_requests += 1
        self.max_observed_concurrency = max(self.max_observed_concurrency, self.active_requests)
        start_time = time.time()

        if wait_ms > 0:
            logger.info(
                "chat_completion_resumed_after_wait",
                request_id=request_id,
                wait_ms=round(wait_ms, 2),
            )
        
        try:
            if request.stream:
                return self._generate_stream(
                    request_id,
                    prompt,
                    request,
                    start_time
                )
            else:
                response = await self._generate_complete(
                    request_id,
                    prompt,
                    request,
                    start_time
                )
                if settings.ENABLE_RESPONSE_CACHE and not request.stream:
                    self._put_cache(cache_key, response)
                return response
        finally:
            self.active_requests -= 1
    
    async def text_completion(
        self,
        request: CompletionRequest
    ) -> CompletionResponse | AsyncIterator[str]:
        """Generate text completion."""
        self.total_requests += 1
        request_id = f"cmpl-{uuid4().hex[:24]}"
        
        logger.info(
            "text_completion_start",
            request_id=request_id,
            prompt_length=len(request.prompt),
            max_tokens=request.max_tokens
        )
        
        model_name = self._select_model_name(getattr(request, 'model', None))
        target_model_path = self._resolve_model_path(model_name)
        model = await model_manager.load_model(model_path=target_model_path)

        wait_ms = await self._wait_for_capacity(request_id, "text_completion")
        
        self.active_requests += 1
        self.max_observed_concurrency = max(self.max_observed_concurrency, self.active_requests)
        start_time = time.time()

        if wait_ms > 0:
            logger.info(
                "text_completion_resumed_after_wait",
                request_id=request_id,
                wait_ms=round(wait_ms, 2),
            )
        
        cache_key = self._cache_key(model_name, request.prompt, request)

        try:
            if request.stream:
                return self._generate_stream_text(
                    request_id,
                    request.prompt,
                    request,
                    start_time
                )
            else:
                if settings.ENABLE_RESPONSE_CACHE:
                    cached = self._response_cache.get(cache_key)
                    if cached:
                        logger.info("response_cache_hit", request_id=request_id, model=model_name)
                        return cached[1]

                response = await self._generate_complete_text(
                    request_id,
                    request.prompt,
                    request,
                    start_time
                )
                if settings.ENABLE_RESPONSE_CACHE:
                    self._put_cache(cache_key, response)
                return response
        finally:
            self.active_requests -= 1
    
    async def _generate_complete(
        self,
        request_id: str,
        prompt: str,
        request: ChatCompletionRequest,
        start_time: float
    ) -> ChatCompletionResponse:
        """Generate complete (non-streaming) chat response."""
        model = model_manager.get_model()
        
        # Add Qwen-specific stop tokens
        stop_tokens = request.stop or []
        if not stop_tokens:
            stop_tokens = ["<|im_end|>", "<|endoftext|>"]
        
        # Run inference in thread pool
        output = await asyncio.to_thread(
            model,
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            stop=stop_tokens,
            echo=False
        )
        
        generated_text = output['choices'][0]['text']
        if request.json_schema:
            generated_text = self._postprocess_with_schema(generated_text, request.json_schema)
        prompt_tokens = output['usage']['prompt_tokens']
        completion_tokens = output['usage']['completion_tokens']
        
        self.total_tokens_generated += completion_tokens
        
        duration = time.time() - start_time
        
        logger.info(
            "chat_completion_complete",
            request_id=request_id,
            duration_seconds=duration,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tokens_per_second=completion_tokens / duration if duration > 0 else 0
        )
        
        return ChatCompletionResponse(
            id=request_id,
            created=int(start_time),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content=generated_text.strip()),
                    finish_reason="stop"
                )
            ],
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
    
    async def _generate_stream(
        self,
        request_id: str,
        prompt: str,
        request: ChatCompletionRequest,
        start_time: float
    ) -> AsyncIterator[str]:
        """Generate streaming chat response."""
        model = model_manager.get_model()
        
        # Stream tokens
        async def generate():
            tokens_generated = 0
            
            for output in model(
                prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                stop=request.stop or [],
                stream=True
            ):
                token = output['choices'][0]['text']
                tokens_generated += 1
                
                # Format as SSE
                chunk = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(start_time),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": token},
                        "finish_reason": None
                    }]
                }
                
                yield f"data: {chunk}\n\n"
            
            # Final chunk
            yield f"data: [DONE]\n\n"
            
            self.total_tokens_generated += tokens_generated
            
            duration = time.time() - start_time
            logger.info(
                "chat_completion_stream_complete",
                request_id=request_id,
                duration_seconds=duration,
                tokens_generated=tokens_generated,
                tokens_per_second=tokens_generated / duration if duration > 0 else 0
            )
        
        return generate()
    
    async def _generate_complete_text(
        self,
        request_id: str,
        prompt: str,
        request: CompletionRequest,
        start_time: float
    ) -> CompletionResponse:
        """Generate complete text completion."""
        model = model_manager.get_model()
        
        output = await asyncio.to_thread(
            model,
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop or [],
            echo=False
        )
        
        generated_text = output['choices'][0]['text']
        if request.json_schema:
            generated_text = self._postprocess_with_schema(generated_text, request.json_schema)
        prompt_tokens = output['usage']['prompt_tokens']
        completion_tokens = output['usage']['completion_tokens']
        
        self.total_tokens_generated += completion_tokens
        
        return CompletionResponse(
            id=request_id,
            created=int(start_time),
            model=request.model,
            choices=[
                CompletionChoice(
                    text=generated_text,
                    index=0,
                    finish_reason="stop"
                )
            ],
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
    
    def _generate_stream_text(self, request_id: str, prompt: str, request: CompletionRequest, start_time: float):
        """Generate streaming text completion."""
        # Similar to _generate_stream but for text completion
        pass
    
    def _messages_to_prompt(self, messages: List[Message]) -> str:
        """
        Convert chat messages to a single prompt string.
        Uses Qwen chat template format: <|im_start|>role\ncontent<|im_end|>
        """
        prompt_parts = []
        
        for message in messages:
            prompt_parts.append(f"<|im_start|>{message.role}\n{message.content}<|im_end|>\n")
        
        # Add assistant start token to prompt for completion
        prompt_parts.append("<|im_start|>assistant\n")
        
        return "".join(prompt_parts)
    
    def get_stats(self) -> Dict:
        """Get inference statistics."""
        uptime_seconds = max(0, int(time.time() - self.started_at))
        queue_capacity = max(1, settings.QUEUE_SIZE)
        virtual_queue_depth = self.waiting_requests
        queue_utilization = min(1.0, virtual_queue_depth / queue_capacity)
        avg_wait_ms = self.total_wait_time_ms / self.wait_events if self.wait_events else 0.0

        return {
            "uptime_seconds": uptime_seconds,
            "active_requests": self.active_requests,
            "waiting_requests": self.waiting_requests,
            "max_observed_concurrency": self.max_observed_concurrency,
            "total_requests": self.total_requests,
            "total_tokens_generated": self.total_tokens_generated,
            "wait_events": self.wait_events,
            "total_wait_time_ms": round(self.total_wait_time_ms, 2),
            "avg_wait_time_ms": round(avg_wait_ms, 2),
            "queue_size": self.queue.qsize(),
            "queue_capacity": queue_capacity,
            "virtual_queue_depth": virtual_queue_depth,
            "queue_utilization": round(queue_utilization, 4),
            "cache_items": len(self._response_cache),
            "model_loaded": model_manager.is_loaded(),
            "model_info": model_manager.get_model_info()
        }

    # ------------------------------------------------------------------
    # Helpers: model selection, caching
    # ------------------------------------------------------------------

    def _select_model_name(self, explicit_model: Optional[str], messages: Optional[List[Message]] = None) -> Optional[str]:
        if explicit_model and explicit_model != "default":
            return explicit_model
        if not settings.ENABLE_ORCHESTRATION:
            return explicit_model or "default"

        corpus = " ".join([m.content for m in messages or []]).lower()
        code_signals = ["code", "json", "typescript", "javascript", "css", "html", "api response", "schema"]
        if any(sig in corpus for sig in code_signals):
            return "qwen-coder"
        return "llama-vision"

    def _resolve_model_path(self, model_name: Optional[str]):
        """Return Path for requested model name or default."""
        if model_name and model_name in settings.MODEL_REGISTRY:
            return settings.MODEL_REGISTRY[model_name]
        return settings.MODEL_PATH

    def _cache_key(self, model_name: Optional[str], prompt: str, request) -> str:
        return f"{model_name}|{hash(prompt)}|{request.temperature}|{getattr(request, 'top_p', '')}|{request.max_tokens}"

    def _put_cache(self, key: str, value):
        if not settings.ENABLE_RESPONSE_CACHE:
            return
        self._response_cache[key] = (time.time(), value)
        if len(self._response_cache) > settings.RESPONSE_CACHE_MAX_ITEMS:
            first_key = next(iter(self._response_cache))
            self._response_cache.pop(first_key, None)

    def _postprocess_with_schema(self, text: str, schema: Dict) -> str:
        """Attempt to return valid JSON matching schema shape (best effort)."""
        cleaned = text.strip()

        # Strip code fences
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z0-9_\-]*\n", "", cleaned)
        cleaned = cleaned.replace("```", "").strip()

        # Try direct parse
        parsed = self._try_json(cleaned)
        if parsed is not None:
            return json.dumps(parsed)

        # Try extracting first JSON object
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            parsed = self._try_json(match.group(0))
            if parsed is not None:
                return json.dumps(parsed)

        # Fallback to original
        return cleaned

    def _try_json(self, payload: str):
        try:
            return json.loads(payload)
        except Exception:
            return None


# Global inference engine
inference_engine = InferenceEngine()
