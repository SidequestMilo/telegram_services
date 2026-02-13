"""
Configuration management for Telegram Gateway Service.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Session Configuration
    SESSION_TTL: int = 86400  # 24 hours in seconds
    
    # Rate Limiting Configuration
    RATE_LIMIT_REQUESTS: int = 1
    RATE_LIMIT_WINDOW: int = 1  # seconds
    
    # Internal Service URLs
    CONVERSATION_SERVICE_URL: str = "http://localhost:8001"
    USER_PROFILE_SERVICE_URL: str = "http://localhost:8002"
    MATCHING_SERVICE_URL: str = "http://localhost:8003"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8004"
    
    # Timeout Configuration (in seconds)
    CONVERSATION_TIMEOUT: int = 5
    MATCHING_TIMEOUT: int = 3
    NOTIFICATION_TIMEOUT: int = 3
    USER_PROFILE_TIMEOUT: int = 3
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    
    # Application Configuration
    APP_NAME: str = "Telegram Gateway"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
