"""
MML - Multi-Model Language System

Advanced AI-powered website generation using local LLMs.
No fallbacks, no keyword matching - pure AI generation.

Models Used:
- Qwen2.5-Coder-7B: Code generation (HTML, CSS, JS)
- Llama-3.2-11B: Understanding and planning

Architecture:
- LLMBackend: Manages model loading and inference
- Agents: Specialized AI agents for each task
- Pipeline: Orchestrates the generation flow
"""

from app.mml.pipeline import MMLPipeline, generate_website

__all__ = ["MMLPipeline", "generate_website"]
