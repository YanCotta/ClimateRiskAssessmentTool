"""FastAPI application setup and configuration."""
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ....config.settings import settings
from .routers import locations, weather, risk

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Initialize FastAPI app
    app = FastAPI(
        title="Climate Risk Assessment API",
        description="API for assessing climate-related risks for locations worldwide.",
        version=settings.API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_PREFIX}/openapi.json"
    )
    
    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(
        locations.router,
        prefix=settings.API_PREFIX
    )
    app.include_router(
        weather.router,
        prefix=settings.API_PREFIX
    )
    app.include_router(
        risk.router,
        prefix=settings.API_PREFIX
    )
    
    # Add health check endpoint
    @app.get(
        "/health",
        status_code=status.HTTP_200_OK,
        tags=["health"]
    )
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT
        }
    
    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, 
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        logger.error(f"Request validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "validation_error",
                "message": "Invalid request data",
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, 
        exc: Exception
    ) -> JSONResponse:
        """Handle all other exceptions."""
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "internal_server_error",
                "message": "An unexpected error occurred",
                "details": str(exc) if settings.DEBUG else "Internal server error"
            }
        )
    
    # Log application startup
    @app.on_event("startup")
    async def startup_event():
        """Handle application startup."""
        logger.info("Starting Climate Risk Assessment API")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        logger.info(f"API Version: {settings.API_VERSION}")
    
    # Log application shutdown
    @app.on_event("shutdown")
    async def shutdown_event():
        """Handle application shutdown."""
        logger.info("Shutting down Climate Risk Assessment API")
    
    return app

# Create application instance
app = create_application()

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "climate_risk.interfaces.api.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
