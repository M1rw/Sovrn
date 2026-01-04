"""
MML LLM Backend

Flexible LLM interface supporting:
1. API providers (OpenAI, Anthropic, OpenRouter) - FAST, recommended
2. Local models via llama-cpp - SLOW, optional

Uses API by default for speed. Set environment variables for your provider.
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass  
class GenerationConfig:
    """Configuration for text generation."""
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9


class LLMBackend:
    """
    Unified LLM backend supporting multiple providers.
    
    Priority:
    1. OpenAI API (if OPENAI_API_KEY set)
    2. Anthropic API (if ANTHROPIC_API_KEY set)
    3. OpenRouter (if OPENROUTER_API_KEY set)
    4. Local model (if USE_LOCAL_MODEL=true)
    5. Smart template fallback
    """
    
    def __init__(self):
        self._client = None
        self._provider = None
        self._local_model = None
        self._setup_provider()
    
    def _setup_provider(self):
        """Setup the best available provider."""
        
        # Try OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                self._client = OpenAI()
                self._provider = "openai"
                self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                print(f"LLM Backend: Using OpenAI ({self._model})")
                return
            except ImportError:
                pass
        
        # Try Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from anthropic import Anthropic
                self._client = Anthropic()
                self._provider = "anthropic"
                self._model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
                print(f"LLM Backend: Using Anthropic ({self._model})")
                return
            except ImportError:
                pass
        
        # Try OpenRouter
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=os.getenv("OPENROUTER_API_KEY")
                )
                self._provider = "openrouter"
                self._model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
                print(f"LLM Backend: Using OpenRouter ({self._model})")
                return
            except ImportError:
                pass
        
        # Try local model
        if os.getenv("USE_LOCAL_MODEL", "").lower() == "true":
            self._provider = "local"
            print("LLM Backend: Will use local model (slow)")
            return
        
        # Fallback to templates
        self._provider = "template"
        print("LLM Backend: Using smart templates (set API keys for AI generation)")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        json_mode: bool = False
    ) -> str:
        """Generate text from a prompt."""
        
        if config is None:
            config = GenerationConfig()
        
        if self._provider == "openai" or self._provider == "openrouter":
            return self._generate_openai(prompt, system_prompt, config, json_mode)
        elif self._provider == "anthropic":
            return self._generate_anthropic(prompt, system_prompt, config, json_mode)
        elif self._provider == "local":
            return self._generate_local(prompt, system_prompt, config, json_mode)
        else:
            # Template fallback - return empty to trigger template logic
            return ""
    
    def _generate_openai(self, prompt: str, system_prompt: Optional[str], config: GenerationConfig, json_mode: bool) -> str:
        """Generate using OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": self._model,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self._client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content
        
        if json_mode:
            text = self._extract_json(text)
        
        return text.strip()
    
    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str], config: GenerationConfig, json_mode: bool) -> str:
        """Generate using Anthropic API."""
        kwargs = {
            "model": self._model,
            "max_tokens": config.max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system_prompt:
            if json_mode:
                system_prompt += "\n\nRespond with valid JSON only."
            kwargs["system"] = system_prompt
        
        response = self._client.messages.create(**kwargs)
        text = response.content[0].text
        
        if json_mode:
            text = self._extract_json(text)
        
        return text.strip()
    
    def _generate_local(self, prompt: str, system_prompt: Optional[str], config: GenerationConfig, json_mode: bool) -> str:
        """Generate using local model."""
        if self._local_model is None:
            self._load_local_model()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self._local_model.create_chat_completion(
            messages=messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )
        
        text = response["choices"][0]["message"]["content"]
        
        if json_mode:
            text = self._extract_json(text)
        
        return text.strip()
    
    def _load_local_model(self):
        """Load local GGUF model."""
        from llama_cpp import Llama
        
        model_path = Path("/workspaces/Sovrn/models/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf")
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        print(f"Loading local model... (this takes 1-2 minutes)")
        self._local_model = Llama(
            model_path=str(model_path),
            n_ctx=4096,
            n_threads=2,
            verbose=False,
            chat_format="chatml"
        )
        print("Model loaded!")
    
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
        return self._provider in ["openai", "anthropic", "openrouter", "local"]


# Global singleton
_backend: Optional[LLMBackend] = None


def get_backend() -> LLMBackend:
    """Get the global LLM backend instance."""
    global _backend
    if _backend is None:
        _backend = LLMBackend()
    return _backend
