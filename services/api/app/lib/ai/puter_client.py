# =============================================================================
# Puter.js AI Client - Primary Cloud Provider
# =============================================================================
"""
Puter.js integration for free cloud AI capabilities.
Puter.js provides free access to GPT-4o-mini, Claude, and other models.

Reference: https://docs.puter.com/AI
"""

import httpx
import json
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class PuterModel(str, Enum):
    """Available Puter.js AI models."""
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    CLAUDE_SONNET = "claude-3-5-sonnet"
    CLAUDE_HAIKU = "claude-3-haiku"
    LLAMA_3_1_405B = "llama-3.1-405b"
    LLAMA_3_1_70B = "llama-3.1-70b"
    MISTRAL_LARGE = "mistral-large-2"
    GEMINI_FLASH = "gemini-1.5-flash"
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_REASONER = "deepseek-reasoner"  # For deep thinking!


@dataclass
class PuterConfig:
    """Puter.js configuration."""
    base_url: str = "https://api.puter.com"
    # Puter.js is FREE - no API key required for basic usage
    # For higher limits, users can authenticate with Puter account
    api_key: Optional[str] = None
    default_model: PuterModel = PuterModel.GPT_4O_MINI
    timeout: int = 120
    max_retries: int = 3
    # Deep thinking model for complex reasoning
    thinking_model: PuterModel = PuterModel.DEEPSEEK_REASONER


@dataclass
class PuterMessage:
    """Chat message for Puter API."""
    role: str  # system, user, assistant
    content: str


@dataclass
class PuterResponse:
    """Response from Puter AI."""
    content: str
    model: str
    thinking: Optional[str] = None  # Deep thinking chain
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0
    success: bool = True
    error: Optional[str] = None


class PuterAI:
    """
    Puter.js AI Client - FREE cloud AI provider.
    
    Features:
    - Free GPT-4o-mini, Claude, Llama access
    - No API keys required for basic usage
    - DeepSeek Reasoner for deep thinking
    - Streaming support
    - Built-in rate limiting
    """
    
    def __init__(self, config: Optional[PuterConfig] = None):
        self.config = config or PuterConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._available = True
        self._last_health_check = 0
        self._health_check_interval = 60  # seconds
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
                
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                timeout=self.config.timeout,
            )
        return self._client
    
    async def check_availability(self) -> bool:
        """Check if Puter.js is available."""
        import time
        current_time = time.time()
        
        # Cache health check result
        if current_time - self._last_health_check < self._health_check_interval:
            return self._available
            
        try:
            client = await self._get_client()
            response = await client.get("/v2/health", timeout=5)
            self._available = response.status_code == 200
        except Exception as e:
            logger.warning("puter_health_check_failed", error=str(e))
            self._available = False
            
        self._last_health_check = current_time
        return self._available
    
    async def chat(
        self,
        messages: List[PuterMessage],
        model: Optional[PuterModel] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        enable_thinking: bool = False,
    ) -> PuterResponse:
        """
        Send chat completion request to Puter.js.
        
        Args:
            messages: List of chat messages
            model: Model to use (default: gpt-4o-mini)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            json_mode: Request JSON output
            enable_thinking: Use deep thinking model
            
        Returns:
            PuterResponse with generated content
        """
        import time
        start_time = time.time()
        
        # Use thinking model if requested
        selected_model = model or (
            self.config.thinking_model if enable_thinking 
            else self.config.default_model
        )
        
        try:
            client = await self._get_client()
            
            # Build request payload
            payload = {
                "model": selected_model.value,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            
            # Puter.js chat endpoint
            response = await client.post(
                "/v2/ai/chat",
                json=payload,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code != 200:
                error_text = response.text
                logger.error("puter_api_error", status=response.status_code, error=error_text)
                return PuterResponse(
                    content="",
                    model=selected_model.value,
                    latency_ms=latency_ms,
                    success=False,
                    error=f"API error {response.status_code}: {error_text}"
                )
            
            data = response.json()
            
            # Extract response content
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            thinking = data.get("thinking", None)  # DeepSeek Reasoner thinking chain
            usage = data.get("usage", {})
            
            logger.info(
                "puter_chat_success",
                model=selected_model.value,
                latency_ms=latency_ms,
                tokens=usage.get("total_tokens", 0)
            )
            
            return PuterResponse(
                content=content,
                model=selected_model.value,
                thinking=thinking,
                usage=usage,
                latency_ms=latency_ms,
                success=True
            )
            
        except httpx.TimeoutException:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error("puter_timeout", model=selected_model.value, latency_ms=latency_ms)
            return PuterResponse(
                content="",
                model=selected_model.value,
                latency_ms=latency_ms,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error("puter_error", error=str(e), latency_ms=latency_ms)
            return PuterResponse(
                content="",
                model=selected_model.value if model else self.config.default_model.value,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
    
    async def stream_chat(
        self,
        messages: List[PuterMessage],
        model: Optional[PuterModel] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """
        Stream chat completion from Puter.js.
        
        Yields:
            Chunks of generated text
        """
        selected_model = model or self.config.default_model
        
        try:
            client = await self._get_client()
            
            payload = {
                "model": selected_model.value,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            async with client.stream("POST", "/v2/ai/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error("puter_stream_error", error=str(e))
            yield f"[Error: {e}]"
    
    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> PuterResponse:
        """
        Generate response with deep thinking chain.
        Uses DeepSeek Reasoner for step-by-step reasoning.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            context: Additional context
            
        Returns:
            PuterResponse with content and thinking chain
        """
        messages = []
        
        if system_prompt:
            messages.append(PuterMessage(role="system", content=system_prompt))
        
        if context:
            messages.append(PuterMessage(
                role="user", 
                content=f"Context:\n{context}\n\nRequest:\n{prompt}"
            ))
        else:
            messages.append(PuterMessage(role="user", content=prompt))
        
        return await self.chat(
            messages=messages,
            model=self.config.thinking_model,
            enable_thinking=True,
            temperature=0.3,  # Lower for reasoning
            max_tokens=8192,  # More tokens for thinking
        )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_puter_ai: Optional[PuterAI] = None


def get_puter_ai() -> PuterAI:
    """Get global Puter AI instance."""
    global _puter_ai
    if _puter_ai is None:
        _puter_ai = PuterAI()
    return _puter_ai
