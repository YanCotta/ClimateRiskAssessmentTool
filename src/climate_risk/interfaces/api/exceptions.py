"""Custom exceptions and exception handlers for the API."""
import logging
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ....config.settings import settings

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors."""
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        message: str = "An error occurred",
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """Initialize the API error.
        
        Args:
            status_code: HTTP status code
            message: Error message
            details: Additional error details
            error_code: Error code for programmatic handling
        """
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        self.error_code = error_code or f"ERR_{status_code}"
        super().__init__(message)

class NotFoundError(APIError):
    """Raised when a resource is not found."""
    
    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[Union[str, int]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the not found error.
        
        Args:
            resource: Name of the resource that was not found
            resource_id: ID of the resource that was not found
            details: Additional error details
        """
        message = f"{resource} not found"
        if resource_id is not None:
            message += f" with id {resource_id}"
            
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            details=details or {},
            error_code="NOT_FOUND",
        )

class ValidationError(APIError):
    """Raised when validation fails."""
    
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the validation error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            details=details or {},
            error_code="VALIDATION_ERROR",
        )

class UnauthorizedError(APIError):
    """Raised when authentication or authorization fails."""
    
    def __init__(
        self,
        message: str = "Not authenticated",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the unauthorized error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            details=details or {},
            error_code="UNAUTHORIZED",
        )

class ForbiddenError(APIError):
    """Raised when the user doesn't have permission to access a resource."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the forbidden error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            details=details or {},
            error_code="FORBIDDEN",
        )

class ConflictError(APIError):
    """Raised when a resource conflict occurs."""
    
    def __init__(
        self,
        message: str = "Resource already exists",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the conflict error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            message=message,
            details=details or {},
            error_code="CONFLICT",
        )

def setup_exception_handlers(app: FastAPI) -> None:
    """Set up exception handlers for the FastAPI application."""
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        """Handle API errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                }
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors.append({
                "field": field or "body",
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation error",
                    "details": {"errors": errors},
                }
            },
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors.append({
                "field": field or "body",
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation error",
                    "details": {"errors": errors},
                }
            },
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all other exceptions."""
        logger.exception(f"Unhandled exception: {str(exc)}")
        
        error_message = "Internal server error"
        if settings.DEBUG:
            error_message = str(exc)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": error_message,
                }
            },
        )
    
    logger.info("Exception handlers setup complete")
