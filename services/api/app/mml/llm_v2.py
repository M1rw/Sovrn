# =============================================================================
# MML LLM Backend v2 - Hybrid AI Integration
# =============================================================================
"""
MML LLM Backend powered by SOVRN Hybrid AI Engine.

Replaces the old multi-provider approach with unified hybrid architecture:
- Puter.js as primary (free, fast, latest models)
- Phi-3-mini as offline backup (100% local)
- Deep thinking for superior website generation

This is a drop-in replacement for the old llm.py
"""

import os
import json
import re
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass  
class GenerationConfig:
    """Configuration for text generation."""
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    mode: str = "balanced"  # fast, balanced, quality, thinking


class LLMBackend:
    """
    Unified LLM backend powered by SOVRN Hybrid AI Engine.
    
    Uses:
    1. Puter.js (cloud) - Free GPT-4o-mini, Claude, etc.
    2. Phi-3-mini (local) - 100% offline fallback
    
    Automatic failover ensures AI is always available.
    """
    
    def __init__(self):
        self._engine = None
        self._initialized = False
        self._provider = "hybrid"  # Always hybrid now
        
    async def _ensure_initialized(self):
        """Initialize the hybrid AI engine."""
        if self._initialized:
            return
            
        from app.lib.ai.providers import get_ai_engine
        self._engine = await get_ai_engine()
        self._initialized = True
        
        status = self._engine.get_status()
        providers = status.get("providers", {})
        
        if providers.get("puter", {}).get("available"):
            print("LLM Backend: Puter.js (cloud) available ✓")
        if providers.get("phi3", {}).get("available"):
            print("LLM Backend: Phi-3 (local) available ✓")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        json_mode: bool = False
    ) -> str:
        """
        Generate text from a prompt (synchronous wrapper).
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            config: Generation configuration
            json_mode: Request JSON output
            
        Returns:
            Generated text
        """
        # Run async in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.agenerate(prompt, system_prompt, config, json_mode)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                self.agenerate(prompt, system_prompt, config, json_mode)
            )
    
    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        json_mode: bool = False
    ) -> str:
        """
        Generate text from a prompt (async).
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            config: Generation configuration
            json_mode: Request JSON output
            
        Returns:
            Generated text
        """
        await self._ensure_initialized()
        
        if config is None:
            config = GenerationConfig()
        
        # Map mode to AIMode
        from app.lib.ai.providers import AIMode
        mode = {
            "fast": AIMode.FAST,
            "balanced": AIMode.BALANCED,
            "quality": AIMode.QUALITY,
            "thinking": AIMode.THINKING,
        }.get(config.mode, AIMode.BALANCED)
        
        response = await self._engine.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            mode=mode,
            json_mode=json_mode,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )
        
        if response.success:
            return response.content
        else:
            # Return empty string to trigger template fallback
            return ""
    
    async def agenerate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate with deep thinking chain.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            context: Additional context
            
        Returns:
            Dict with content and thinking
        """
        await self._ensure_initialized()
        
        from app.lib.ai.providers import AIMode
        
        response = await self._engine.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            context=context,
            mode=AIMode.THINKING,
        )
        
        return {
            "content": response.content,
            "thinking": response.thinking,
            "success": response.success,
            "error": response.error,
            "provider": response.provider.value,
            "model": response.model,
            "latency_ms": response.latency_ms,
        }
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text."""
        # Try to find JSON block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json_match.group(1).strip()
        
        # Try to find raw JSON object
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            return brace_match.group(0)
        
        return text
    
    @property
    def is_ai_enabled(self) -> bool:
        """Check if AI generation is available."""
        return True  # Always true with hybrid - at least local works
    
    def get_status(self) -> Dict[str, Any]:
        """Get backend status."""
        if not self._initialized:
            return {
                "initialized": False,
                "provider": "hybrid",
            }
        
        return {
            "initialized": True,
            "provider": "hybrid",
            "engine_status": self._engine.get_status(),
        }


# Global singleton
_backend: Optional[LLMBackend] = None


def get_backend() -> LLMBackend:
    """Get the global LLM backend instance."""
    global _backend
    if _backend is None:
        _backend = LLMBackend()
    return _backend


# Async version
async def get_backend_async() -> LLMBackend:
    """Get the global LLM backend instance (async)."""
    backend = get_backend()
    await backend._ensure_initialized()
    return backend
