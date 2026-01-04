# =============================================================================
# Hybrid AI Engine - Unified Provider with Automatic Fallback
# =============================================================================
"""
Hybrid AI architecture that combines:
- Puter.js (primary) - Free cloud AI, fast, latest models
- Phi-3-mini (backup) - 100% offline, always available

Automatic failover ensures AI is always available.
"""

import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import structlog
import os

from .puter_client import PuterAI, PuterMessage, PuterResponse, PuterModel, get_puter_ai
from .phi3_client import Phi3LocalAI, Phi3Response, get_phi3_ai

logger = structlog.get_logger()


class AIProvider(str, Enum):
    """Available AI providers."""
    PUTER = "puter"         # Cloud AI (Puter.js)
    PHI3_LOCAL = "phi3"     # Local AI (Phi-3-mini)
    AUTO = "auto"           # Automatic selection


class AIMode(str, Enum):
    """AI generation modes."""
    FAST = "fast"           # Quick response
    BALANCED = "balanced"   # Good quality/speed balance
    QUALITY = "quality"     # Best quality, slower
    THINKING = "thinking"   # Deep reasoning mode


@dataclass
class AIResponse:
    """Unified AI response."""
    content: str
    provider: AIProvider
    model: str
    thinking: Optional[str] = None
    latency_ms: int = 0
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "provider": self.provider.value,
            "model": self.model,
            "thinking": self.thinking,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class HybridConfig:
    """Hybrid AI configuration."""
    primary_provider: AIProvider = AIProvider.PUTER
    fallback_provider: AIProvider = AIProvider.PHI3_LOCAL
    enable_fallback: bool = True
    fallback_on_timeout: bool = True
    fallback_timeout_ms: int = 30000
    preload_fallback: bool = True
    # Model preferences
    fast_model: PuterModel = PuterModel.GPT_4O_MINI
    quality_model: PuterModel = PuterModel.CLAUDE_SONNET
    thinking_model: PuterModel = PuterModel.DEEPSEEK_REASONER


class HybridAIEngine:
    """
    Hybrid AI Engine - Smart provider orchestration.
    
    Features:
    - Automatic provider selection based on availability
    - Seamless fallback from cloud to local
    - Multiple generation modes (fast, quality, thinking)
    - Unified response format
    - Health monitoring
    - Parallel capability checking
    """
    
    def __init__(self, config: Optional[HybridConfig] = None):
        self.config = config or HybridConfig()
        self._puter: Optional[PuterAI] = None
        self._phi3: Optional[Phi3LocalAI] = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        
        # Provider status
        self._puter_available = False
        self._phi3_available = False
        
        # Stats
        self._stats = {
            "puter_requests": 0,
            "puter_failures": 0,
            "phi3_requests": 0,
            "phi3_failures": 0,
            "fallbacks": 0,
        }
    
    async def initialize(self):
        """Initialize AI providers."""
        async with self._init_lock:
            if self._initialized:
                return
            
            logger.info("initializing_hybrid_ai_engine")
            
            # Initialize providers in parallel
            tasks = []
            
            # Puter.js (cloud)
            self._puter = get_puter_ai()
            tasks.append(self._check_puter_availability())
            
            # Phi-3 (local) - preload if configured
            self._phi3 = get_phi3_ai()
            if self.config.preload_fallback:
                tasks.append(self._preload_phi3())
            else:
                tasks.append(self._check_phi3_availability())
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            self._initialized = True
            
            logger.info(
                "hybrid_ai_initialized",
                puter_available=self._puter_available,
                phi3_available=self._phi3_available
            )
    
    async def _check_puter_availability(self):
        """Check Puter.js availability."""
        try:
            self._puter_available = await self._puter.check_availability()
        except Exception as e:
            logger.warning("puter_availability_check_failed", error=str(e))
            self._puter_available = False
    
    async def _check_phi3_availability(self):
        """Check Phi-3 model availability."""
        info = self._phi3.get_info()
        self._phi3_available = info["model_exists"]
    
    async def _preload_phi3(self):
        """Preload Phi-3 model for instant fallback."""
        try:
            self._phi3_available = await self._phi3.load()
        except Exception as e:
            logger.warning("phi3_preload_failed", error=str(e))
            self._phi3_available = self._phi3.get_info()["model_exists"]
    
    def _select_provider(self, preferred: AIProvider = AIProvider.AUTO) -> AIProvider:
        """Select the best available provider."""
        if preferred == AIProvider.PUTER and self._puter_available:
            return AIProvider.PUTER
        elif preferred == AIProvider.PHI3_LOCAL and self._phi3_available:
            return AIProvider.PHI3_LOCAL
        elif preferred == AIProvider.AUTO:
            # Auto: prefer Puter, fallback to Phi3
            if self._puter_available:
                return AIProvider.PUTER
            elif self._phi3_available:
                return AIProvider.PHI3_LOCAL
        
        # If preferred not available, try any available
        if self._puter_available:
            return AIProvider.PUTER
        elif self._phi3_available:
            return AIProvider.PHI3_LOCAL
        
        # Nothing available
        return AIProvider.PHI3_LOCAL  # Will fail gracefully
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        mode: AIMode = AIMode.BALANCED,
        provider: AIProvider = AIProvider.AUTO,
        json_mode: bool = False,
        max_tokens: int = 4096,
        temperature: Optional[float] = None,
    ) -> AIResponse:
        """
        Generate AI response with automatic provider selection and fallback.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            context: Additional context
            mode: Generation mode (fast, balanced, quality, thinking)
            provider: Preferred provider (auto for automatic)
            json_mode: Request JSON output
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            AIResponse with generated content
        """
        if not self._initialized:
            await self.initialize()
        
        # Select provider
        selected_provider = self._select_provider(provider)
        
        # Set temperature based on mode
        if temperature is None:
            temperature = {
                AIMode.FAST: 0.7,
                AIMode.BALANCED: 0.6,
                AIMode.QUALITY: 0.4,
                AIMode.THINKING: 0.3,
            }.get(mode, 0.6)
        
        # Try primary provider
        if selected_provider == AIProvider.PUTER:
            response = await self._generate_puter(
                prompt, system_prompt, context, mode, json_mode, max_tokens, temperature
            )
            
            # Fallback on failure
            if not response.success and self.config.enable_fallback and self._phi3_available:
                logger.info("falling_back_to_phi3", reason=response.error)
                self._stats["fallbacks"] += 1
                response = await self._generate_phi3(
                    prompt, system_prompt, context, mode, json_mode, max_tokens, temperature
                )
                response.metadata["fallback"] = True
            
            return response
        else:
            return await self._generate_phi3(
                prompt, system_prompt, context, mode, json_mode, max_tokens, temperature
            )
    
    async def _generate_puter(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[str],
        mode: AIMode,
        json_mode: bool,
        max_tokens: int,
        temperature: float,
    ) -> AIResponse:
        """Generate using Puter.js."""
        self._stats["puter_requests"] += 1
        
        # Select model based on mode
        model = {
            AIMode.FAST: self.config.fast_model,
            AIMode.BALANCED: PuterModel.GPT_4O_MINI,
            AIMode.QUALITY: self.config.quality_model,
            AIMode.THINKING: self.config.thinking_model,
        }.get(mode, PuterModel.GPT_4O_MINI)
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append(PuterMessage(role="system", content=system_prompt))
        
        user_content = prompt
        if context:
            user_content = f"Context:\n{context}\n\nRequest:\n{prompt}"
        messages.append(PuterMessage(role="user", content=user_content))
        
        # Use thinking mode for THINKING
        use_thinking = mode == AIMode.THINKING
        
        try:
            if use_thinking:
                response = await self._puter.generate_with_thinking(
                    prompt, system_prompt, context
                )
            else:
                response = await self._puter.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
            
            if not response.success:
                self._stats["puter_failures"] += 1
            
            return AIResponse(
                content=response.content,
                provider=AIProvider.PUTER,
                model=response.model,
                thinking=response.thinking,
                latency_ms=response.latency_ms,
                tokens_used=response.usage.get("total_tokens", 0),
                success=response.success,
                error=response.error,
            )
            
        except Exception as e:
            self._stats["puter_failures"] += 1
            logger.error("puter_generate_error", error=str(e))
            return AIResponse(
                content="",
                provider=AIProvider.PUTER,
                model=model.value,
                success=False,
                error=str(e),
            )
    
    async def _generate_phi3(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[str],
        mode: AIMode,
        json_mode: bool,
        max_tokens: int,
        temperature: float,
    ) -> AIResponse:
        """Generate using Phi-3 local model."""
        self._stats["phi3_requests"] += 1
        
        try:
            # Use thinking mode for THINKING
            if mode == AIMode.THINKING:
                response = await self._phi3.generate_with_thinking(
                    prompt, system_prompt, context
                )
            else:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                user_content = prompt
                if context:
                    user_content = f"Context:\n{context}\n\nRequest:\n{prompt}"
                messages.append({"role": "user", "content": user_content})
                
                response = await self._phi3.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
            
            if not response.success:
                self._stats["phi3_failures"] += 1
            
            return AIResponse(
                content=response.content,
                provider=AIProvider.PHI3_LOCAL,
                model="phi-3-mini-4k-instruct",
                thinking=response.thinking,
                latency_ms=response.latency_ms,
                tokens_used=response.tokens_generated + response.tokens_prompt,
                success=response.success,
                error=response.error,
            )
            
        except Exception as e:
            self._stats["phi3_failures"] += 1
            logger.error("phi3_generate_error", error=str(e))
            return AIResponse(
                content="",
                provider=AIProvider.PHI3_LOCAL,
                model="phi-3-mini-4k-instruct",
                success=False,
                error=str(e),
            )
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: AIProvider = AIProvider.PUTER,
    ) -> AsyncIterator[str]:
        """
        Stream AI response.
        Note: Only Puter.js supports streaming currently.
        
        Yields:
            Chunks of generated text
        """
        if not self._initialized:
            await self.initialize()
        
        if provider == AIProvider.PUTER and self._puter_available:
            messages = []
            if system_prompt:
                messages.append(PuterMessage(role="system", content=system_prompt))
            messages.append(PuterMessage(role="user", content=prompt))
            
            async for chunk in self._puter.stream_chat(messages):
                yield chunk
        else:
            # Fallback: generate full response and yield at once
            response = await self.generate(prompt, system_prompt)
            yield response.content
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        return {
            "initialized": self._initialized,
            "providers": {
                "puter": {
                    "available": self._puter_available,
                    "type": "cloud",
                },
                "phi3": {
                    "available": self._phi3_available,
                    "type": "local",
                    "loaded": self._phi3.is_loaded if self._phi3 else False,
                }
            },
            "config": {
                "primary": self.config.primary_provider.value,
                "fallback_enabled": self.config.enable_fallback,
            },
            "stats": self._stats,
        }
    
    async def shutdown(self):
        """Shutdown and cleanup."""
        logger.info("shutting_down_hybrid_ai_engine")
        
        if self._puter:
            await self._puter.close()
        
        if self._phi3:
            await self._phi3.unload()
        
        self._initialized = False


# Singleton instance
_engine: Optional[HybridAIEngine] = None


async def get_ai_engine() -> HybridAIEngine:
    """Get global Hybrid AI Engine instance."""
    global _engine
    if _engine is None:
        _engine = HybridAIEngine()
        await _engine.initialize()
    return _engine
