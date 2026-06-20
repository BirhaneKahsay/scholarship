"""
Configuration management for the Scholarship Agent.
Handles environment variables, validation, and settings.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = {
        "extra": "ignore",
        "env_file": ".env",
        "case_sensitive": False,
    }

    # OpenAI Configuration
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")

    # Tavily Web Search
    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")

    # Telegram Configuration
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHANNEL_ID")
    telegram_group_id: Optional[str] = Field(default=None, alias="TELEGRAM_GROUP_ID")

    # PostgreSQL Configuration
    database_url: str = Field(..., alias="DATABASE_URL")
    sqlalchemy_echo: bool = Field(default=False, alias="SQLALCHEMY_ECHO")

    # Application Configuration
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Scheduler Configuration
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_first_run_hour: int = Field(default=8, alias="SCHEDULER_FIRST_RUN_HOUR")
    scheduler_first_run_minute: int = Field(default=0, alias="SCHEDULER_FIRST_RUN_MINUTE")
    scheduler_second_run_hour: int = Field(default=17, alias="SCHEDULER_SECOND_RUN_HOUR")
    scheduler_second_run_minute: int = Field(default=0, alias="SCHEDULER_SECOND_RUN_MINUTE")
    scheduler_timezone: str = Field(default="UTC", alias="SCHEDULER_TIMEZONE")

    # Search Configuration
    max_search_results: int = Field(default=50, alias="MAX_SEARCH_RESULTS")
    search_terms_rotation_enabled: bool = Field(
        default=True, alias="SEARCH_TERMS_ROTATION_ENABLED"
    )

    # Fact Checking Configuration
    fact_check_enabled: bool = Field(default=True, alias="FACT_CHECK_ENABLED")
    deadline_check_enabled: bool = Field(default=True, alias="DEADLINE_CHECK_ENABLED")

    # Duplicate Detection
    duplicate_check_enabled: bool = Field(default=True, alias="DUPLICATE_CHECK_ENABLED")
    duplicate_threshold: float = Field(default=0.85, alias="DUPLICATE_THRESHOLD")

    # API Timeouts (seconds)
    web_search_timeout: int = Field(default=30, alias="WEB_SEARCH_TIMEOUT")
    llm_timeout: int = Field(default=60, alias="LLM_TIMEOUT")
    database_timeout: int = Field(default=10, alias="DATABASE_TIMEOUT")

    # Rate Limiting
    openai_max_retries: int = Field(default=3, alias="OPENAI_MAX_RETRIES")
    openai_retry_delay: int = Field(default=2, alias="OPENAI_RETRY_DELAY")

    @property
    def scheduler_first_run_time(self) -> str:
        """Return formatted first run time (HH:MM)."""
        return f"{self.scheduler_first_run_hour:02d}:{self.scheduler_first_run_minute:02d}"

    @property
    def scheduler_second_run_time(self) -> str:
        """Return formatted second run time (HH:MM)."""
        return f"{self.scheduler_second_run_hour:02d}:{self.scheduler_second_run_minute:02d}"

    @validator("duplicate_threshold")
    def validate_duplicate_threshold(cls, v):
        """Ensure duplicate threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("duplicate_threshold must be between 0 and 1")
        return v

    @validator("openai_model")
    def validate_openai_model(cls, v):
        """Validate OpenAI model selection."""
        valid_models = ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo",'openai/gpt-5.5']
        if v not in valid_models:
            raise ValueError(f"openai_model must be one of {valid_models}")
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache ensures we only load settings once.
    """
    return Settings()


def setup_logging(settings: Settings) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/app.log"),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {settings.environment} environment")
    return logger


# Initialize settings and logger
try:
    settings = get_settings()
    logger = setup_logging(settings)
except Exception as e:
    print(f"Failed to load settings: {e}")
    print("Please ensure .env file is properly configured")
    raise

