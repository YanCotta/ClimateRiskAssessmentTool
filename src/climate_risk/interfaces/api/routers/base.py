"""Base router with common dependencies and utilities."""
from typing import Any, Dict, Optional, Type, TypeVar, Generic
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ....application.services.base import ServiceError

T = TypeVar('T', bound=BaseModel)

class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = Query(1, ge=1, description="Page number")
    size: int = Query(10, ge=1, le=100, description="Items per page")

class BaseRouter:
    """Base router with common functionality for all API endpoints."""
    
    def __init__(self, prefix: str = "", tags: Optional[list[str]] = None):
        """Initialize the base router."""
        self.router = APIRouter(prefix=prefix, tags=tags or [])
    
    @staticmethod
    def handle_service_error(error: ServiceError) -> None:
        """Handle service errors and convert to HTTP exceptions."""
        status_code = status.HTTP_400_BAD_REQUEST
        
        # Map error codes to status codes
        error_code_map = {
            "not_found": status.HTTP_404_NOT_FOUND,
            "already_exists": status.HTTP_409_CONFLICT,
            "unauthorized": status.HTTP_401_UNAUTHORIZED,
            "forbidden": status.HTTP_403_FORBIDDEN,
            "validation_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
        }
        
        status_code = error_code_map.get(error.code, status.HTTP_400_BAD_REQUEST)
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": error.code or "service_error",
                "message": error.message,
                "details": error.details
            }
        )
    
    def create_route(self, *args, **kwargs):
        """Decorator to create a route with error handling."""
        def decorator(func):
            async def wrapper(*func_args, **func_kwargs):
                try:
                    return await func(*func_args, **func_kwargs)
                except ServiceError as e:
                    self.handle_service_error(e)
                except Exception as e:
                    # Log the unexpected error
                    print(f"Unexpected error: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail={
                            "code": "internal_server_error",
                            "message": "An unexpected error occurred",
                            "details": str(e)
                        }
                    )
            
            # Copy the original function's docstring and signature
            wrapper.__doc__ = func.__doc__
            wrapper.__name__ = func.__name__
            wrapper.__signature__ = func.__signature__
            
            # Create the route with the wrapped function
            return self.router.api_route(*args, **kwargs)(wrapper)
        return decorator

class CRUDRouter(BaseRouter, Generic[T]):
    """Base CRUD router with common CRUD operations."""
    
    def __init__(
        self, 
        service_class: Type[Any],
        response_model: Type[T],
        create_model: Type[BaseModel],
        update_model: Type[BaseModel],
        prefix: str = "",
        tags: Optional[list[str]] = None
    ):
        """Initialize the CRUD router."""
        super().__init__(prefix=prefix, tags=tags or [])
        self.service_class = service_class
        self.response_model = response_model
        self.create_model = create_model
        self.update_model = update_model
        
        # Register CRUD routes
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Register CRUD routes."""
        
        @self.router.get(
            "/{id}", 
            response_model=self.response_model,
            summary=f"Get {self.response_model.__name__} by ID"
        )
        async def get_by_id(id: str, service: self.service_class = Depends()):
            """Get an item by ID."""
            return await service.get_by_id(id)
        
        @self.router.get(
            "/", 
            response_model=list[self.response_model],
            summary=f"List {self.response_model.__name__}s"
        )
        async def list_items(
            skip: int = 0,
            limit: int = 100,
            service: self.service_class = Depends()
        ):
            """List items with pagination."""
            return await service.list(skip=skip, limit=limit)
        
        @self.router.post(
            "/", 
            response_model=self.response_model,
            status_code=status.HTTP_201_CREATED,
            summary=f"Create a new {self.response_model.__name__}"
        )
        async def create(
            item: self.create_model,
            service: self.service_class = Depends()
        ):
            """Create a new item."""
            return await service.create(item)
        
        @self.router.put(
            "/{id}", 
            response_model=self.response_model,
            summary=f"Update an existing {self.response_model.__name__}"
        )
        async def update(
            id: str,
            item: self.update_model,
            service: self.service_class = Depends()
        ):
            """Update an existing item."""
            return await service.update(id, item)
        
        @self.router.delete(
            "/{id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary=f"Delete a {self.response_model.__name__}"
        )
        async def delete(id: str, service: self.service_class = Depends()):
            """Delete an item by ID."""
            await service.delete(id)
            return None
