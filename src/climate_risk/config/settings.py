"""Application settings management using Pydantic."""
from typing import List, Optional, Any, Dict, Tuple, Union
from functools import lru_cache
from enum import Enum
from pydantic import AnyHttpUrl, validator, field_validator, Field, RedisDsn, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
from pathlib import Path


class EnvironmentType(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class RateLimitStorageType(str, Enum):
    """Rate limiting storage backends."""
    MEMORY = "memory"
    REDIS = "redis"

class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    PROJECT_NAME: str = "Climate Risk Assessment Tool"
    VERSION: str = "0.1.0"
    
    # API Configuration
    API_PREFIX: str = "/api/v1"
    API_VERSION: str = "1.0.0"
    API_TITLE: str = "Climate Risk Assessment API"
    API_DESCRIPTION: str = "API for assessing climate-related risks"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production!
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # API Versioning
    API_VERSION_HEADER: str = "X-API-Version"
    API_VERSION_PARAM: str = "version"
    API_DEFAULT_VERSION: str = "1.0.0"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE: RateLimitStorageType = RateLimitStorageType.MEMORY
    RATE_LIMIT_DEFAULT: Tuple[int, int] = (100, 60)  # 100 requests per minute
    RATE_LIMIT_WHITELIST: List[str] = ["127.0.0.1", "localhost"]
    RATE_LIMIT_HEADERS_ENABLED: bool = True
    
    # Redis Configuration (for rate limiting)
    REDIS_URL: Optional[RedisDsn] = None
    REDIS_POOL_SIZE: int = 10
    REDIS_POOL_TIMEOUT: int = 5  # seconds
    
    # Database Configuration
    DATABASE_URL: Optional[PostgresDsn] = "postgresql+asyncpg://postgres:postgres@localhost:5432/climate_risk"
    
    # CORS (Cross-Origin Resource Sharing)
    CORS_ORIGINS: List[AnyHttpUrl] = []
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str) and v.startswith("[") and v.endswith("]"):
            # Handle JSON array string
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return []
    
    # Weather API Configuration
    WEATHER_API_KEY: str
    WEATHER_API_BASE_URL: str = "https://api.weather.com"
    WEATHER_API_TIMEOUT: int = 10  # seconds
    
    # Model Configuration
    MODEL_CACHE_TTL: int = 3600  # 1 hour
    MODEL_CACHE_ENABLED: bool = True
    
    # Logging Configuration
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_JSON_FORMAT: bool = False
    
    # Request/Response Logging
    LOG_REQUESTS: bool = True
    LOG_RESPONSES: bool = False  # Be careful with sensitive data
    
    # Security Headers
    SECURE_HEADERS: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "same-origin",
    }
    
    # Performance
    MAX_WORKERS: int = 4
    WORKER_TIMEOUT: int = 30  # seconds
    
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
        extra="ignore",
        env_nested_delimiter="__",
        env_prefix="CLIMATE_RISK_",
    )
    
    @property
    def is_production(self) -> bool:
        """Check if the application is running in production mode."""
        return self.ENVIRONMENT == EnvironmentType.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if the application is running in development mode."""
        return self.ENVIRONMENT == EnvironmentType.DEVELOPMENT
    
    @property
    def is_testing(self) -> bool:
        """Check if the application is running in testing mode."""
        return self.ENVIRONMENT == EnvironmentType.TESTING
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        return {
            "allow_origins": [str(origin) for origin in self.CORS_ORIGINS],
            "allow_credentials": self.CORS_ALLOW_CREDENTIALS,
            "allow_methods": self.CORS_ALLOW_METHODS,
            "allow_headers": self.CORS_ALLOW_HEADERS,
        }

@lru_cache()
def get_settings() -> Settings:
    """Get application settings.
    
    This function is cached to prevent reading the environment multiple times.
    
    Returns:
        Settings: The application settings instance.
    """
    return Settings()

def configure_logging(settings: Settings) -> None:
    """Configure logging based on settings."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    if settings.LOG_JSON_FORMAT:
        import json_log_formatter
        formatter = json_log_formatter.JSONFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logging.basicConfig(handlers=[handler], level=log_level)
    else:
        logging.basicConfig(
            level=log_level,
            format=settings.LOG_FORMAT,
        )
    
    # Set log level for external libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# Global settings object
settings = get_settings()

# Configure logging
configure_logging(settings)

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.info(
    "Loaded settings for %s environment", 
    settings.ENVIRONMENT.value if hasattr(settings.ENVIRONMENT, 'value') else settings.ENVIRONMENT
)
