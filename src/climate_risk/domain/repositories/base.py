"""Base repository interfaces for the domain."""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any
from uuid import UUID

from ....domain.entities.base import BaseEntity, PaginatedResponse

T = TypeVar('T', bound=BaseEntity)

class Repository(Generic[T], ABC):
    """Base repository interface for CRUD operations."""
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def list(
        self, 
        *, 
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs
    ) -> List[T]:
        """List entities with optional filtering and pagination."""
        pass
    
    @abstractmethod
    async def paginate(
        self,
        *,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 10,
        **kwargs
    ) -> PaginatedResponse[T]:
        """Get paginated list of entities with optional filtering."""
        pass
    
    @abstractmethod
    async def create(self, entity: T, **kwargs) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    async def update(self, id: str, entity: T, **kwargs) -> Optional[T]:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, id: str, **kwargs) -> bool:
        """Delete an entity by ID."""
        pass

class LocationRepository(Repository['Location'], ABC):
    """Repository interface for Location entities."""
    
    @abstractmethod
    async def get_by_coordinates(
        self, 
        latitude: float, 
        longitude: float,
        **kwargs
    ) -> Optional['Location']:
        """Get location by coordinates."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        **kwargs
    ) -> List['Location']:
        """Search locations by name or other attributes."""
        pass

class WeatherDataRepository(Repository['WeatherData'], ABC):
    """Repository interface for WeatherData entities."""
    
    @abstractmethod
    async def get_for_location(
        self,
        location_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs
    ) -> List['WeatherData']:
        """Get weather data for a location within a date range."""
        pass
    
    @abstractmethod
    async def get_latest_for_location(
        self,
        location_id: str,
        **kwargs
    ) -> Optional['WeatherData']:
        """Get the most recent weather data for a location."""
        pass

class RiskAssessmentRepository(Repository['RiskAssessment'], ABC):
    """Repository interface for RiskAssessment entities."""
    
    @abstractmethod
    async def get_for_location(
        self,
        location_id: str,
        valid_at: Optional[str] = None,
        **kwargs
    ) -> List['RiskAssessment']:
        """Get risk assessments for a location, optionally filtered by validity date."""
        pass
    
    @abstractmethod
    async def get_latest_for_location(
        self,
        location_id: str,
        **kwargs
    ) -> Optional['RiskAssessment']:
        """Get the most recent risk assessment for a location."""
        pass
