# =============================================================================
# SOVRN Inference Service - Configuration
# =============================================================================
"""
Configuration for the inference service using llama.cpp
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Inference service settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # ==========================================================================
    # Server
    # ==========================================================================
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console

    CORS_ORIGINS: List[str] = Field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:8000",
    ])
    CORS_ALLOW_CREDENTIALS: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # ==========================================================================
    # Model Configuration
    # ==========================================================================
    MODEL_PATH: Path = Field(
        default=Path("/models/phi-3-mini-4k-instruct-q4.gguf"),
        description="Default model path used when no model name is specified"
    )

    MODEL_REGISTRY: Dict[str, Path] = Field(
        default_factory=lambda: {
            "phi-3-mini": Path("/models/phi-3-mini-4k-instruct-q4.gguf"),
            "phi-3-mini-4bit": Path("/models/phi-3-mini-4k-instruct-q4.gguf"),
            "qwen-coder": Path("/models/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"),
        },
        description="Mapping of model name to absolute GGUF path"
    )

    ENABLE_ORCHESTRATION: bool = Field(
        default=False,
        description="If true, pick model automatically based on request intent"
    )
    
    # Alternative models (can be swapped)
    MODELS_DIR: Path = Field(
        default=Path("/models"),
        description="Directory containing all model files"
    )
    
    # Model parameters
    CONTEXT_LENGTH: int = Field(
        default=4096,
        description="Maximum context length"
    )
    
    MAX_TOKENS: int = Field(
        default=4096,
        description="Maximum tokens to generate"
    )
    
    # Performance tuning
    N_GPU_LAYERS: int = Field(
        default=0,
        description="Number of layers to offload to GPU (0 = CPU only)"
    )
    
    N_THREADS: int = Field(
        default=4,
        description="Number of CPU threads to use"
    )
    
    N_BATCH: int = Field(
        default=512,
        description="Batch size for prompt processing"
    )
    
    # Memory management
    USE_MMAP: bool = Field(
        default=True,
        description="Use memory-mapped file loading"
    )
    
    USE_MLOCK: bool = Field(
        default=False,
        description="Lock model in RAM (prevents swapping)"
    )
    
    # ==========================================================================
    # Inference Defaults
    # ==========================================================================
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TOP_P: float = 0.95
    DEFAULT_TOP_K: int = 40
    DEFAULT_REPEAT_PENALTY: float = 1.1
    
    # ==========================================================================
    # Queue & Concurrency
    # ==========================================================================
    MAX_CONCURRENT_REQUESTS: int = Field(
        default=4,
        description="Maximum concurrent inference requests"
    )
    
    REQUEST_TIMEOUT_SECONDS: int = Field(
        default=300,
        description="Timeout for single request (5 minutes)"
    )
    
    QUEUE_SIZE: int = Field(
        default=100,
        description="Maximum queued requests"
    )
    
    # ==========================================================================
    # Caching
    # ==========================================================================
    ENABLE_PROMPT_CACHE: bool = Field(
        default=True,
        description="Cache prompt embeddings"
    )

    # Simple response cache (in-memory) to reuse identical prompts
    ENABLE_RESPONSE_CACHE: bool = Field(default=True)
    RESPONSE_CACHE_MAX_ITEMS: int = Field(default=128)
    
    CACHE_SIZE_MB: int = Field(
        default=512,
        description="Prompt cache size in MB"
    )
    
    # ==========================================================================
    # Monitoring
    # ==========================================================================
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    
    METRICS_PORT: int = 9090


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
