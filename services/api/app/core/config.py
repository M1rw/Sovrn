# =============================================================================
# SOVRN API - Configuration
# =============================================================================
"""
Application configuration using Pydantic Settings.
All values can be overridden via environment variables.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import AliasChoices, Field, PostgresDsn, field_validator, model_validator
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
    # Observability
    # ==========================================================================
    OBSERVABILITY_TRACE_PROPAGATION_ENABLED: bool = True
    OBSERVABILITY_HTTP_METRICS_ENABLED: bool = True
    OBSERVABILITY_HTTP_METRICS_SAMPLE_LIMIT: int = Field(default=1000, ge=100, le=50000)
    
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
    
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"])
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            parsed = [origin.strip() for origin in v.split(",") if origin.strip()]
            return parsed or ["http://localhost:3000", "http://localhost:8000"]
        return v

    @model_validator(mode="after")
    def ensure_database_url(self) -> "Settings":
        if self.DATABASE_URL is None and self.SUPABASE_DB_URL is None:
            raise ValueError("Either DATABASE_URL or SUPABASE_DB_URL must be configured.")
        return self

    @property
    def effective_database_url(self) -> str:
        database_url = self.DATABASE_URL or self.SUPABASE_DB_URL
        if database_url is None:
            raise RuntimeError("Database URL is not configured.")
        return str(database_url)
    
    # ==========================================================================
    # Database
    # ==========================================================================
    DATABASE_URL: Optional[PostgresDsn] = None
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # ==========================================================================
    # Supabase (optional managed backend)
    # ==========================================================================
    SUPABASE_ENABLED: bool = False
    SUPABASE_URL: Optional[str] = None
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_DB_URL: Optional[PostgresDsn] = None
    
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
    # AI Chat Prompt Assembly
    # ==========================================================================
    AI_PROMPT_ASSEMBLY_ON: bool = False

    # ==========================================================================
    # AI Structured Shadow Parsing
    # ==========================================================================
    AI_STRUCTURED_SHADOW_ENABLED: bool = False

    # ==========================================================================
    # AI Shadow Action Resolution
    # ==========================================================================
    AI_ACTION_RESOLUTION_SHADOW_ENABLED: bool = False

    # ==========================================================================
    # AI Shadow Telemetry and Quality Gates
    # ==========================================================================
    AI_STRUCTURED_SHADOW_METRICS_ENABLED: bool = False
    AI_SHADOW_METRICS_MIN_SAMPLE_SIZE: int = 3000
    AI_SHADOW_MIN_PARSE_SUCCESS_RATE: float = Field(default=0.99, ge=0, le=1)
    AI_SHADOW_MAX_REPAIR_RATE: float = Field(default=0.08, ge=0, le=1)
    AI_SHADOW_MAX_PARSE_FAILURE_RATE: float = Field(default=0.005, ge=0, le=1)
    AI_SHADOW_MAX_ACTION_MISMATCH_RATE: float = Field(default=0.20, ge=0, le=1)

    # ==========================================================================
    # AI Conversation Persistence
    # ==========================================================================
    AI_STATE_PERSIST_ENABLED: bool = False

    # ==========================================================================
    # AI Conversation Summarization (Non-Authoritative)
    # ==========================================================================
    AI_SUMMARIZATION_ENABLED: bool = False
    AI_SUMMARY_TRIGGER_EVERY_TURNS: int = Field(default=6, ge=1, le=1000)

    # ==========================================================================
    # AI Context Compaction (Summary + Recent Turns)
    # ==========================================================================
    AI_CONTEXT_COMPACTION_ENABLED: bool = False
    AI_CONTEXT_COMPACTION_RECENT_TURNS: int = Field(default=4, ge=1, le=50)

    # ==========================================================================
    # AI Structured Response Contract Rollout
    # ==========================================================================
    AI_RESOLVED_ACTION_RESPONSE_ENABLED: bool = False

    # ==========================================================================
    # Preview Runtime Bootstrap
    # ==========================================================================
    PREVIEW_SESSION_TOKEN_TTL_SECONDS: int = Field(default=600, ge=60, le=3600)
    PREVIEW_SESSION_TOKEN_MAX_TTL_SECONDS: int = Field(default=3600, ge=60, le=86400)
    PREVIEW_BUILD_TIMEOUT_SECONDS: int = Field(default=20, ge=1, le=300)
    PREVIEW_BUILD_MAX_FILES: int = Field(default=12, ge=1, le=200)
    PREVIEW_BUILD_MAX_TOTAL_BYTES: int = Field(default=786432, ge=1024, le=10485760)
    PREVIEW_BUILD_MAX_FILE_BYTES: int = Field(default=262144, ge=1024, le=5242880)

    # ==========================================================================
    # Multi-Agent Orchestration (AQE + Lane Scheduling)
    # ==========================================================================
    ORCHESTRATION_RUNTIME_ENABLED: bool = Field(
        default=True,
        validation_alias=AliasChoices("ORCHESTRATION_RUNTIME_ENABLED", "PHASE4_ORCHESTRATION_ENABLED"),
    )
    ORCHESTRATION_AQE_ENABLED: bool = Field(
        default=True,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_ENABLED", "PHASE4_AQE_ENABLED"),
    )
    ORCHESTRATION_AQE_INFERENCE_STATS_TIMEOUT_SECONDS: int = Field(
        default=2,
        ge=1,
        le=30,
        validation_alias=AliasChoices(
            "ORCHESTRATION_AQE_INFERENCE_STATS_TIMEOUT_SECONDS",
            "PHASE4_AQE_INFER_STATS_TIMEOUT_SECONDS",
        ),
    )

    ORCHESTRATION_REQUEST_TIME_BUDGET_SECONDS: int = Field(
        default=180,
        ge=10,
        le=900,
        validation_alias=AliasChoices("ORCHESTRATION_REQUEST_TIME_BUDGET_SECONDS", "PHASE4_REQUEST_TIME_BUDGET_SECONDS"),
    )
    ORCHESTRATION_STAGE_TIMEOUT_SECONDS: int = Field(
        default=45,
        ge=5,
        le=300,
        validation_alias=AliasChoices("ORCHESTRATION_STAGE_TIMEOUT_SECONDS", "PHASE4_STAGE_TIMEOUT_SECONDS"),
    )

    ORCHESTRATION_CRITIC_MAX_ATTEMPTS: int = Field(
        default=2,
        ge=1,
        le=8,
        validation_alias=AliasChoices("ORCHESTRATION_CRITIC_MAX_ATTEMPTS", "PHASE4_CRITIC_MAX_ATTEMPTS"),
    )
    ORCHESTRATION_CRITIC_STRICT_FAIL: bool = Field(
        default=False,
        validation_alias=AliasChoices("ORCHESTRATION_CRITIC_STRICT_FAIL", "PHASE4_CRITIC_STRICT_FAIL"),
    )

    ORCHESTRATION_LANE_PRIORITY_INTERACTIVE: int = Field(
        default=100,
        ge=0,
        le=1000,
        validation_alias=AliasChoices("ORCHESTRATION_LANE_PRIORITY_INTERACTIVE", "PHASE4_LANE_PRIORITY_INTERACTIVE"),
    )
    ORCHESTRATION_LANE_PRIORITY_QUALITY: int = Field(
        default=55,
        ge=0,
        le=1000,
        validation_alias=AliasChoices("ORCHESTRATION_LANE_PRIORITY_QUALITY", "PHASE4_LANE_PRIORITY_QUALITY"),
    )
    ORCHESTRATION_LANE_PRIORITY_BACKGROUND: int = Field(
        default=15,
        ge=0,
        le=1000,
        validation_alias=AliasChoices("ORCHESTRATION_LANE_PRIORITY_BACKGROUND", "PHASE4_LANE_PRIORITY_BACKGROUND"),
    )

    ORCHESTRATION_AQE_Q0_QUEUE_DEPTH: int = Field(
        default=25,
        ge=1,
        le=10000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q0_QUEUE_DEPTH", "PHASE4_AQE_Q0_QUEUE_DEPTH"),
    )
    ORCHESTRATION_AQE_Q1_QUEUE_DEPTH: int = Field(
        default=12,
        ge=1,
        le=10000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q1_QUEUE_DEPTH", "PHASE4_AQE_Q1_QUEUE_DEPTH"),
    )
    ORCHESTRATION_AQE_Q2_QUEUE_DEPTH: int = Field(
        default=5,
        ge=1,
        le=10000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q2_QUEUE_DEPTH", "PHASE4_AQE_Q2_QUEUE_DEPTH"),
    )

    ORCHESTRATION_AQE_Q0_WAITING_REQUESTS: int = Field(
        default=10,
        ge=1,
        le=10000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q0_WAITING_REQUESTS", "PHASE4_AQE_Q0_WAITING_REQUESTS"),
    )
    ORCHESTRATION_AQE_Q1_WAITING_REQUESTS: int = Field(
        default=5,
        ge=1,
        le=10000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q1_WAITING_REQUESTS", "PHASE4_AQE_Q1_WAITING_REQUESTS"),
    )
    ORCHESTRATION_AQE_Q2_WAITING_REQUESTS: int = Field(
        default=2,
        ge=1,
        le=10000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q2_WAITING_REQUESTS", "PHASE4_AQE_Q2_WAITING_REQUESTS"),
    )

    ORCHESTRATION_AQE_Q0_AVG_WAIT_MS: int = Field(
        default=3500,
        ge=100,
        le=600000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q0_AVG_WAIT_MS", "PHASE4_AQE_Q0_AVG_WAIT_MS"),
    )
    ORCHESTRATION_AQE_Q1_AVG_WAIT_MS: int = Field(
        default=1500,
        ge=100,
        le=600000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q1_AVG_WAIT_MS", "PHASE4_AQE_Q1_AVG_WAIT_MS"),
    )
    ORCHESTRATION_AQE_Q2_AVG_WAIT_MS: int = Field(
        default=650,
        ge=50,
        le=600000,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q2_AVG_WAIT_MS", "PHASE4_AQE_Q2_AVG_WAIT_MS"),
    )

    ORCHESTRATION_AQE_Q0_QUEUE_UTILIZATION: float = Field(
        default=0.9,
        ge=0,
        le=1,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q0_QUEUE_UTILIZATION", "PHASE4_AQE_Q0_QUEUE_UTILIZATION"),
    )
    ORCHESTRATION_AQE_Q1_QUEUE_UTILIZATION: float = Field(
        default=0.7,
        ge=0,
        le=1,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q1_QUEUE_UTILIZATION", "PHASE4_AQE_Q1_QUEUE_UTILIZATION"),
    )
    ORCHESTRATION_AQE_Q2_QUEUE_UTILIZATION: float = Field(
        default=0.4,
        ge=0,
        le=1,
        validation_alias=AliasChoices("ORCHESTRATION_AQE_Q2_QUEUE_UTILIZATION", "PHASE4_AQE_Q2_QUEUE_UTILIZATION"),
    )
    
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
