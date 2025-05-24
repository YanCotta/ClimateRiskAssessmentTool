"""Base service classes for application services."""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Any, Dict, List

from ....domain.entities.base import BaseEntity, PaginatedResponse

T = TypeVar('T', bound=BaseEntity)

class ServiceError(Exception):
    """Base exception for service layer errors."""
    def __init__(self, message: str, code: str = None, details: Any = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(self.message)

class BaseService(Generic[T], ABC):
    """Base service class with common CRUD operations."""
    
    def __init__(self, repository):
        self.repository = repository
    
    async def get_by_id(self, id: str, **kwargs) -> Optional[T]:
        """Get entity by ID."""
        try:
            return await self.repository.get_by_id(id, **kwargs)
        except Exception as e:
            raise ServiceError(
                message=f"Failed to get entity with ID {id}",
                code="entity_not_found",
                details=str(e)
            )
    
    async def list(
        self, 
        *, 
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs
    ) -> List[T]:
        """List entities with optional filtering and pagination."""
        try:
            return await self.repository.list(
                filters=filters,
                skip=skip,
                limit=limit,
                **kwargs
            )
        except Exception as e:
            raise ServiceError(
                message="Failed to list entities",
                code="list_entities_failed",
                details=str(e)
            )
    
    async def paginate(
        self,
        *,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 10,
        **kwargs
    ) -> PaginatedResponse[T]:
        """Get paginated list of entities with optional filtering."""
        try:
            return await self.repository.paginate(
                filters=filters,
                page=page,
                size=size,
                **kwargs
            )
        except Exception as e:
            raise ServiceError(
                message="Failed to get paginated entities",
                code="paginate_entities_failed",
                details=str(e)
            )
    
    async def create(self, entity: T, **kwargs) -> T:
        """Create a new entity."""
        try:
            return await self.repository.create(entity, **kwargs)
        except Exception as e:
            raise ServiceError(
                message="Failed to create entity",
                code="create_entity_failed",
                details=str(e)
            )
    
    async def update(self, id: str, entity: T, **kwargs) -> Optional[T]:
        """Update an existing entity."""
        try:
            return await self.repository.update(id, entity, **kwargs)
        except Exception as e:
            raise ServiceError(
                message=f"Failed to update entity with ID {id}",
                code="update_entity_failed",
                details=str(e)
            )
    
    async def delete(self, id: str, **kwargs) -> bool:
        """Delete an entity by ID."""
        try:
            return await self.repository.delete(id, **kwargs)
        except Exception as e:
            raise ServiceError(
                message=f"Failed to delete entity with ID {id}",
                code="delete_entity_failed",
                details=str(e)
            )
