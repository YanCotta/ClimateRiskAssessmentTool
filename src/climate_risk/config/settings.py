"""Application settings management using Pydantic."""
from typing import List, Optional, Any, Dict
from functools import lru_cache
from pydantic import AnyHttpUrl, validator, field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
from pathlib import Path

class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    PROJECT_NAME: str = "Climate Risk Assessment Tool"
    VERSION: str = "0.1.0"
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production!
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS (Cross-Origin Resource Sharing)
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Weather API Configuration
    WEATHER_API_KEY: str
    WEATHER_API_BASE_URL: str = "https://api.weather.com"
    
    # Model Configuration
    MODEL_CACHE_TTL: int = 3600  # 1 hour
    
    # Logging Configuration
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MODELS_DIR: Path = BASE_DIR / "models"
    
    # Ensure directories exist
    @field_validator('DATA_DIR', 'MODELS_DIR', mode='after')
    def ensure_dirs_exist(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    # Pydantic config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    ""
    Get application settings.
    
    This function is cached to prevent reading the environment multiple times.
    """
    return Settings()

# Global settings object
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
)

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.info(f"Loaded settings for {settings.ENVIRONMENT} environment")
