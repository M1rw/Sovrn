# =============================================================================
# SOVRN Hybrid AI Engine
# =============================================================================
"""
Hybrid AI architecture with:
- Puter.js as primary (free cloud AI)
- Phi-3-mini as offline backup
- Deep thinking orchestration for website generation
"""

from .providers import HybridAIEngine, AIProvider, AIResponse, AIMode, get_ai_engine
from .deep_thinking import DeepThinkingEngine, ThinkingStep, ThinkingPhase
from .puter_client import PuterAI
from .phi3_client import Phi3LocalAI

__all__ = [
    "HybridAIEngine",
    "AIProvider", 
    "AIResponse",
    "AIMode",
    "get_ai_engine",
    "DeepThinkingEngine",
    "ThinkingStep",
    "ThinkingPhase",
    "PuterAI",
    "Phi3LocalAI"
]
