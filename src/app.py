"""Main FastAPI application entry point for the Climate Risk Assessment Tool."""
import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute

from .config import settings
from .infrastructure.database.session import get_db, init_db
from .interfaces.api.routers import locations, weather, risk
from .interfaces.api.middleware import (
    LoggingMiddleware,
    VersioningMiddleware,
    RateLimitMiddleware,
    get_rate_limiter
)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """Create and configure the FastAPI application.
    
    This factory function creates and configures the FastAPI application with all
    necessary middleware, routes, and event handlers.
    
    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    # Configure FastAPI application
    app = FastAPI(
        title="Climate Risk Assessment API",
        description="API for assessing climate-related risks for locations",
        version=settings.API_VERSION,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        debug=settings.DEBUG,
    )
    
    # Configure CORS middleware
    configure_cors(app)
    
    # Add custom middleware
    configure_middleware(app)
    
    # Include API routers
    configure_routers(app)
    
    # Add health check endpoint
    configure_health_check(app)
    
    # Configure lifespan events
    configure_lifespan(app)
    
    return app


def configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware."""
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def configure_middleware(app: FastAPI) -> None:
    """Configure application middleware."""
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add versioning middleware
    app.add_middleware(
        VersioningMiddleware,
        default_version=settings.API_VERSION,
        version_param="version",
        version_header="Accept",
        version_regex=r"^v(\d+(\.\d+)*)$",
    )
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        default_limits={"default": (100, 60)},  # 100 requests per minute
        storage=settings.RATE_LIMIT_STORAGE,
        redis_url=getattr(settings, "REDIS_URL", None),
    )


def configure_routers(app: FastAPI) -> None:
    """Configure API routers."""
    # Mount static files (if any)
    app.mount(
        "/static",
        StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
        name="static"
    )
    
    # Include API routers
    app.include_router(
        locations.router,
        prefix=f"{settings.API_PREFIX}/locations",
        tags=["locations"]
    )
    app.include_router(
        weather.router,
        prefix=f"{settings.API_PREFIX}/weather",
        tags=["weather"]
    )
    app.include_router(
        risk.router,
        prefix=f"{settings.API_PREFIX}/risk",
        tags=["risk"]
    )


def configure_health_check(app: FastAPI) -> None:
    """Configure health check endpoint."""
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
        }


def configure_lifespan(app: FastAPI) -> None:
    """Configure application lifespan events."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info("Starting up Climate Risk Assessment API...")
        
        try:
            # Initialize database
            await init_db()
            logger.info("Database initialization completed successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
            
        logger.info("Startup completed")
        
        yield
        
        # Shutdown
        logger.info("Shutting down Climate Risk Assessment API...")
        # Add any cleanup code here
    
    # Set the lifespan context manager
    app.router.lifespan_context = lifespan


# Create the FastAPI application
app = create_application()



# Dependency injection
get_db_session = get_db

# Main entry point for running with uvicorn programmatically
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
