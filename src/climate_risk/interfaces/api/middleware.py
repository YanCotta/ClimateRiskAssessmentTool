"""API middleware for request/response handling and logging."""
import time
import logging
import json
from typing import Callable, Awaitable, Any, Dict, Optional

from fastapi import Request, Response, status
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ....config.settings import settings

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process each request and log details."""
        # Skip logging for health checks and metrics endpoints
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Log request details
        client_host = request.client.host if request.client else "unknown"
        logger.info(
            f"Request: {request.method} {request.url.path} from {client_host}"
        )
        
        # Log request body if present and not too large
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await request.body()
                if len(request_body) > 0:
                    # Log only the first 1000 bytes to avoid logging large bodies
                    logger.debug(f"Request body: {request_body[:1000]}")
            except Exception as e:
                logger.warning(f"Failed to log request body: {e}")
        
        # Process the request and time it
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response details
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"status_code={response.status_code} "
            f"process_time={process_time:.4f}s"
        )
        
        # Add process time to response headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling and logging errors."""
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle errors and log them appropriately."""
        try:
            return await call_next(request)
        except Exception as e:
            # Log the full exception
            logger.exception(f"Unhandled exception: {str(e)}")
            
            # Return a 500 Internal Server Error
            return Response(
                content=json.dumps({
                    "detail": "Internal server error",
                    "error": str(e)
                }),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json"
            )

class LoggingRoute(APIRoute):
    """Custom route class that logs request and response details."""
    
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        """Get route handler with logging."""
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # Log request details
            logger.info(
                f"Route: {request.method} {request.url.path} "
                f"params={dict(request.query_params)}"
            )
            
            # Process the request and time it
            start_time = time.time()
            response = await original_route_handler(request)
            process_time = time.time() - start_time
            
            # Log response details
            logger.info(
                f"Route completed: {request.method} {request.url.path} "
                f"status_code={response.status_code} "
                f"process_time={process_time:.4f}s"
            )
            
            return response
        
        return custom_route_handler

def setup_middleware(app: ASGIApp) -> None:
    """Set up middleware for the FastAPI application."""
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add error handling middleware (only in production)
    if not settings.DEBUG:
        app.add_middleware(ErrorHandlingMiddleware)
    
    # Configure logging
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Set log level for uvicorn and fastapi loggers
    logging.getLogger("uvicorn").setLevel(settings.LOG_LEVEL)
    logging.getLogger("fastapi").setLevel(settings.LOG_LEVEL)
    
    logger.info("Middleware setup complete")
