# =============================================================================
# SOVRN Worker - Configuration
# =============================================================================
"""
Worker configuration settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Worker settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Database
    DATABASE_URL: str
    
    # Services
    INFERENCE_URL: str = Field(default="http://infer:8080")
    API_URL: str = Field(default="http://api:8000")
    
    # Worker
    POLL_INTERVAL: int = Field(default=2, ge=1, le=300)  # seconds
    JOB_TIMEOUT: int = Field(default=300, ge=5, le=3600)  # seconds
    MAX_RETRIES: int = Field(default=3, ge=0, le=20)

    # Observability
    WORKER_METRICS_LOG_INTERVAL_SECONDS: int = Field(default=30, ge=5, le=3600)
    WORKER_TRACE_PROPAGATION_ENABLED: bool = True
    
    # Debugging
    DEBUG: bool = False
    
    # Artifacts
    ARTIFACTS_PATH: str = "/var/artifacts"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


settings = Settings()
