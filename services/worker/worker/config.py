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
        case_sensitive=True,
        extra="ignore"
    )
    
    # Database
    DATABASE_URL: str
    
    # Services
    INFERENCE_URL: str = "http://infer:8080"
    API_URL: str = "http://api:8000"
    
    # Worker
    POLL_INTERVAL: int = 2  # seconds
    JOB_TIMEOUT: int = 300  # 5 minutes
    MAX_RETRIES: int = 3
    
    # Debugging
    DEBUG: bool = False
    
    # Artifacts
    ARTIFACTS_PATH: str = "/var/artifacts"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    DEBUG: bool = False


settings = Settings()
