"""Main FastAPI application entry point for the Climate Risk Assessment Tool."""
import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config.settings import settings
from .infrastructure.database.session import get_db, init_db
from .interfaces.api.routers import locations, weather, risk
from .interfaces.api.middleware import LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Climate Risk Assessment API",
    description="API for assessing climate-related risks for locations",
    version=settings.API_VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# Add CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add logging middleware
app.add_middleware(LoggingMiddleware)

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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
    }

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application services on startup."""
    logger.info("Starting up Climate Risk Assessment API...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    logger.info("Startup completed")

# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application services on shutdown."""
    logger.info("Shutting down Climate Risk Assessment API...")
    # Add any cleanup code here

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
