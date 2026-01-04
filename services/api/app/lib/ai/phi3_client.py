# =============================================================================
# Phi-3-mini Local AI Client - Offline Backup
# =============================================================================
"""
Phi-3-mini quantized model for 100% offline inference.
Fast, efficient, runs on CPU with good quality.

Model: microsoft/Phi-3-mini-4k-instruct (Q4_K_M quantized)
"""

import asyncio
import json
import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
import structlog

logger = structlog.get_logger()


@dataclass
class Phi3Config:
    """Phi-3-mini configuration."""
    model_path: Path = field(default_factory=lambda: Path(
        os.environ.get("PHI3_MODEL_PATH", "/workspaces/Sovrn/models/phi-3-mini-4k-instruct-q4.gguf")
    ))
    context_length: int = 4096
    n_threads: int = 4
    n_gpu_layers: int = 0  # CPU-only by default
    n_batch: int = 512
    use_mmap: bool = True
    use_mlock: bool = False
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    # Chat format for Phi-3 (uses ChatML format)
    chat_format: str = "chatml"


@dataclass
class Phi3Response:
    """Response from Phi-3 model."""
    content: str
    thinking: Optional[str] = None
    tokens_generated: int = 0
    tokens_prompt: int = 0
    latency_ms: int = 0
    success: bool = True
    error: Optional[str] = None


class Phi3LocalAI:
    """
    Phi-3-mini Local AI - 100% Offline Inference.
    
    Features:
    - Fast CPU inference with llama.cpp
    - Quantized for efficiency (Q4_K_M ~2.4GB)
    - Good quality for code and reasoning
    - Simulated deep thinking mode
    - Zero network dependency
    """
    
    def __init__(self, config: Optional[Phi3Config] = None):
        self.config = config or Phi3Config()
        self._model = None
        self._loaded = False
        self._loading = False
        self._load_lock = asyncio.Lock()
        
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded and self._model is not None
    
    async def load(self) -> bool:
        """
        Load the Phi-3 model asynchronously.
        
        Returns:
            True if loaded successfully
        """
        if self._loaded:
            return True
            
        async with self._load_lock:
            if self._loaded:
                return True
                
            if self._loading:
                # Wait for other load to complete
                while self._loading:
                    await asyncio.sleep(0.1)
                return self._loaded
            
            self._loading = True
            
            try:
                # Check if model exists
                if not self.config.model_path.exists():
                    logger.error("phi3_model_not_found", path=str(self.config.model_path))
                    self._loading = False
                    return False
                
                logger.info(
                    "loading_phi3_model",
                    path=str(self.config.model_path),
                    threads=self.config.n_threads
                )
                
                # Load model in thread pool
                self._model = await asyncio.to_thread(self._load_model_sync)
                self._loaded = True
                
                logger.info(
                    "phi3_model_loaded",
                    vocab_size=self._model.n_vocab(),
                    ctx_length=self._model.n_ctx()
                )
                
                return True
                
            except Exception as e:
                logger.error("phi3_load_error", error=str(e))
                return False
            finally:
                self._loading = False
    
    def _load_model_sync(self):
        """Synchronous model loading."""
        from llama_cpp import Llama
        
        return Llama(
            model_path=str(self.config.model_path),
            n_ctx=self.config.context_length,
            n_threads=self.config.n_threads,
            n_gpu_layers=self.config.n_gpu_layers,
            n_batch=self.config.n_batch,
            use_mmap=self.config.use_mmap,
            use_mlock=self.config.use_mlock,
            verbose=False,
            chat_format=self.config.chat_format,
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> Phi3Response:
        """
        Generate chat completion with Phi-3.
        
        Args:
            messages: List of {"role": str, "content": str}
            temperature: Override default temperature
            max_tokens: Max tokens to generate
            json_mode: Request JSON output
            
        Returns:
            Phi3Response with generated content
        """
        import time
        start_time = time.time()
        
        # Ensure model is loaded
        if not await self.load():
            return Phi3Response(
                content="",
                success=False,
                error="Model not loaded"
            )
        
        try:
            # Add JSON instruction if needed
            if json_mode and messages:
                last_msg = messages[-1]
                if not "JSON" in last_msg["content"]:
                    messages[-1] = {
                        "role": last_msg["role"],
                        "content": last_msg["content"] + "\n\nRespond with valid JSON only."
                    }
            
            # Run inference in thread pool
            response = await asyncio.to_thread(
                self._model.create_chat_completion,
                messages=messages,
                temperature=temperature or self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                max_tokens=max_tokens,
                repeat_penalty=self.config.repeat_penalty,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            content = response["choices"][0]["message"]["content"]
            usage = response.get("usage", {})
            
            # Extract JSON if needed
            if json_mode:
                content = self._extract_json(content)
            
            logger.info(
                "phi3_chat_success",
                latency_ms=latency_ms,
                tokens=usage.get("completion_tokens", 0)
            )
            
            return Phi3Response(
                content=content,
                tokens_generated=usage.get("completion_tokens", 0),
                tokens_prompt=usage.get("prompt_tokens", 0),
                latency_ms=latency_ms,
                success=True
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error("phi3_chat_error", error=str(e), latency_ms=latency_ms)
            return Phi3Response(
                content="",
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
    
    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Phi3Response:
        """
        Generate with simulated deep thinking.
        Uses chain-of-thought prompting for reasoning.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            context: Additional context
            
        Returns:
            Phi3Response with content and thinking chain
        """
        # Build chain-of-thought prompt
        thinking_prompt = """You are an expert AI assistant that thinks step-by-step.

For complex tasks, follow this process:
1. UNDERSTAND: Restate what's being asked
2. ANALYZE: Break down the requirements
3. PLAN: Outline your approach
4. EXECUTE: Implement the solution
5. VERIFY: Check your work

Think through each step carefully before responding."""

        messages = [
            {"role": "system", "content": thinking_prompt + (f"\n\n{system_prompt}" if system_prompt else "")}
        ]
        
        user_content = prompt
        if context:
            user_content = f"Context:\n{context}\n\nRequest:\n{prompt}"
        
        # Add thinking instruction
        user_content += "\n\nThink step-by-step, then provide your final answer."
        
        messages.append({"role": "user", "content": user_content})
        
        response = await self.chat(
            messages=messages,
            temperature=0.3,  # Lower for reasoning
            max_tokens=4096,
        )
        
        # Extract thinking from response
        if response.success:
            thinking, answer = self._extract_thinking(response.content)
            response.thinking = thinking
            response.content = answer
        
        return response
    
    def _extract_thinking(self, text: str) -> tuple[Optional[str], str]:
        """Extract thinking chain from response."""
        # Look for thinking patterns
        patterns = [
            r"(?:UNDERSTAND|Understanding|Step 1).*?(?=(?:Final Answer|ANSWER|Solution))",
            r"<thinking>(.*?)</thinking>",
            r"```thinking\n(.*?)```",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                thinking = match.group(0) if match.lastindex is None else match.group(1)
                answer = text.replace(thinking, "").strip()
                return thinking.strip(), answer
        
        return None, text
    
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
    
    async def unload(self):
        """Unload model and free memory."""
        if self._model:
            del self._model
            self._model = None
            self._loaded = False
            logger.info("phi3_model_unloaded")
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "loaded": self._loaded,
            "model_path": str(self.config.model_path),
            "model_exists": self.config.model_path.exists(),
            "context_length": self.config.context_length,
            "threads": self.config.n_threads,
            "gpu_layers": self.config.n_gpu_layers,
        }


# Singleton instance
_phi3_ai: Optional[Phi3LocalAI] = None


def get_phi3_ai() -> Phi3LocalAI:
    """Get global Phi-3 AI instance."""
    global _phi3_ai
    if _phi3_ai is None:
        _phi3_ai = Phi3LocalAI()
    return _phi3_ai
