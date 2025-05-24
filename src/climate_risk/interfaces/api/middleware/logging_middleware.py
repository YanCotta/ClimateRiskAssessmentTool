"""Logging middleware for FastAPI."""
import time
import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from uuid import uuid4

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ....config.settings import settings

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.
    
    This middleware logs detailed information about each request and response,
    including method, path, status code, and timing information.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        *,
        logger: Optional[logging.Logger] = None,
        request_log_level: int = logging.INFO,
        response_log_level: int = logging.INFO,
        log_request_body: bool = False,
        log_response_body: bool = False,
        sensitive_headers: set = None,
        exclude_paths: set = None,
        **kwargs: Any
    ) -> None:
        """Initialize the logging middleware.
        
        Args:
            app: The ASGI application.
            logger: Logger instance to use. If not provided, a default logger will be used.
            request_log_level: Log level for request logs.
            response_log_level: Log level for response logs.
            log_request_body: Whether to log request bodies.
            log_response_body: Whether to log response bodies.
            sensitive_headers: Set of header names that should be redacted.
            exclude_paths: Set of paths that should not be logged.
            **kwargs: Additional arguments to pass to the base class.
        """
        super().__init__(app, **kwargs)
        self.logger = logger or logging.getLogger(__name__)
        self.request_log_level = request_log_level
        self.response_log_level = response_log_level
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.sensitive_headers = sensitive_headers or {"authorization", "cookie", "set-cookie"}
        self.exclude_paths = exclude_paths or {"/health", "/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and log information about it and the response."""
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Generate a unique request ID
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Log request information
        await self._log_request(request, request_id)
        
        # Process the request and time it
        start_time = time.time()
        response = await self._process_request(request, call_next)
        process_time = (time.time() - start_time) * 1000
        
        # Log response information
        await self._log_response(request, response, process_time, request_id)
        
        return response
    
    async def _process_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and handle any exceptions."""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            self.logger.exception(
                "Unhandled exception while processing request",
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                }
            )
            raise
    
    async def _log_request(self, request: Request, request_id: str) -> None:
        """Log information about the incoming request."""
        # Prepare request data
        request_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client": f"{request.client.host}:{request.client.port}" if request.client else None,
            "headers": self._filter_headers(request.headers),
        }
        
        # Log request body if enabled
        if self.log_request_body and request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if body:
                    try:
                        request_data["body"] = json.loads(body)
                    except json.JSONDecodeError:
                        request_data["body"] = body.decode(errors="replace")
            except Exception as e:
                self.logger.warning(
                    "Failed to log request body",
                    extra={"request_id": request_id, "error": str(e)},
                    exc_info=True
                )
        
        # Log the request
        self.logger.log(
            self.request_log_level,
            "Request received",
            extra={"request": request_data},
        )
    
    async def _log_response(
        self, request: Request, response: Response, process_time: float, request_id: str
    ) -> None:
        """Log information about the outgoing response."""
        # Prepare response data
        response_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time, 2),
            "headers": self._filter_headers(response.headers),
        }
        
        # Log response body if enabled and it's an error response
        if self.log_response_body and 400 <= response.status_code < 600:
            try:
                body = getattr(response, "body", b"")
                if body:
                    try:
                        response_data["body"] = json.loads(body)
                    except (json.JSONDecodeError, AttributeError):
                        response_data["body"] = body.decode(errors="replace")
            except Exception as e:
                self.logger.warning(
                    "Failed to log response body",
                    extra={"request_id": request_id, "error": str(e)},
                    exc_info=True
                )
        
        # Log the response
        log_level = (
            logging.ERROR if 500 <= response.status_code < 600 else
            logging.WARNING if 400 <= response.status_code < 500 else
            self.response_log_level
        )
        
        self.logger.log(
            log_level,
            f"{request.method} {request.url.path} {response.status_code}",
            extra={"response": response_data},
        )
    
    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter sensitive headers from being logged."""
        return {
            k: "[REDACTED]" if k.lower() in self.sensitive_headers else v
            for k, v in headers.items()
            not k.lower().startswith("x-")
        }


def get_logging_middleware(
    app: ASGIApp,
    logger: Optional[logging.Logger] = None,
    **kwargs: Any
) -> LoggingMiddleware:
    """Get a configured logging middleware instance.
    
    This is a convenience function to create and configure the logging middleware
    with settings from the application configuration.
    
    Args:
        app: The ASGI application.
        logger: Logger instance to use. If not provided, a default logger will be used.
        **kwargs: Additional arguments to pass to the LoggingMiddleware.
    
    Returns:
        LoggingMiddleware: Configured logging middleware instance.
    """
    return LoggingMiddleware(
        app,
        logger=logger,
        request_log_level=logging.INFO,
        response_log_level=logging.INFO,
        log_request_body=getattr(settings, "LOG_REQUESTS", False),
        log_response_body=getattr(settings, "LOG_RESPONSES", False),
        sensitive_headers={"authorization", "cookie", "set-cookie", "x-api-key"},
        exclude_paths={"/health", "/docs", "/openapi.json", "/redoc", "/metrics"},
        **kwargs
    )
