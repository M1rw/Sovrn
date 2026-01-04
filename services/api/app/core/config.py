# =============================================================================
# SOVRN API - Configuration
# =============================================================================
"""
Application configuration using Pydantic Settings.
All values can be overridden via environment variables.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # ==========================================================================
    # General
    # ==========================================================================
    APP_NAME: str = "SOVRN"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="production", alias="NODE_ENV")
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console
    
    # ==========================================================================
    # Server
    # ==========================================================================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # ==========================================================================
    # Security
    # ==========================================================================
    JWT_SECRET: str = Field(default="sovrn-dev-secret-key-change-in-production-32chars", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # ==========================================================================
    # Database
    # ==========================================================================
    DATABASE_URL: PostgresDsn
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    
    # ==========================================================================
    # Redis (optional)
    # ==========================================================================
    REDIS_URL: Optional[str] = None
    
    # ==========================================================================
    # Inference Service
    # ==========================================================================
    INFERENCE_URL: str = "http://infer:8080"
    ALT_INFERENCE_URL: Optional[str] = None
    INFERENCE_TIMEOUT: int = 300  # 5 minutes for long generations
    
    # ==========================================================================
    # Sparks (Monetization)
    # ==========================================================================
    SPARKS_FREE: int = 3
    SPARKS_FREELANCER: int = 30
    SPARKS_BUSINESS: int = 100
    SPARKS_AGENCY: int = -1  # Unlimited
    
    SPARK_COST_BASIC: int = 1
    SPARK_COST_ADVANCED: int = 3
    SPARK_COST_PREMIUM: int = 5
    
    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_GENERATIONS_PER_HOUR: int = 10
    
    # ==========================================================================
    # File Storage
    # ==========================================================================
    ARTIFACTS_PATH: str = "/var/artifacts"
    MAX_ARTIFACT_SIZE_MB: int = 100
    ARTIFACT_RETENTION_DAYS: int = 30
    
    # ==========================================================================
    # Email (optional)
    # ==========================================================================
    SMTP_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@sovrn.local"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
