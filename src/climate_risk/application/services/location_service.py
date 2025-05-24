"""Location service implementation."""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ....domain.entities.location import Location, LocationType, GeoPoint
from ....domain.repositories import LocationRepository
from ..services.base import BaseService, ServiceError
from ....config.settings import settings

logger = logging.getLogger(__name__)

class LocationService(BaseService[Location]):
    """Service for location-related operations."""
    
    def __init__(self, repository: LocationRepository):
        super().__init__(repository)
    
    async def get_by_coordinates(
        self, 
        latitude: float, 
        longitude: float,
        **kwargs
    ) -> Optional[Location]:
        """Get location by coordinates."""
        try:
            return await self.repository.get_by_coordinates(
                latitude=latitude,
                longitude=longitude,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to get location by coordinates: {e}")
            raise ServiceError(
                message="Failed to get location by coordinates",
                code="get_location_by_coordinates_failed",
                details=str(e)
            )
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        **kwargs
    ) -> List[Location]:
        """Search locations by name or other attributes."""
        try:
            return await self.repository.search(
                query=query,
                limit=limit,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Location search failed: {e}")
            raise ServiceError(
                message="Location search failed",
                code="location_search_failed",
                details=str(e)
            )
    
    async def create_or_update_location(
        self,
        location_data: Dict[str, Any],
        **kwargs
    ) -> Location:
        """Create or update a location."""
        try:
            # Check if location with same coordinates exists
            if 'geometry' in location_data and 'coordinates' in location_data['geometry']:
                lon, lat = location_data['geometry']['coordinates'][:2]
                existing = await self.get_by_coordinates(latitude=lat, longitude=lon)
                
                if existing:
                    # Update existing location
                    for key, value in location_data.items():
                        if hasattr(existing, key) and key != 'id':
                            setattr(existing, key, value)
                    return await self.update(existing.id, existing, **kwargs)
            
            # Create new location
            location = Location(**location_data)
            return await self.create(location, **kwargs)
            
        except Exception as e:
            logger.error(f"Failed to create or update location: {e}")
            raise ServiceError(
                message="Failed to create or update location",
                code="create_or_update_location_failed",
                details=str(e)
            )
    
    async def get_or_create_location(
        self,
        name: str,
        latitude: float,
        longitude: float,
        location_type: LocationType = LocationType.CITY,
        **kwargs
    ) -> Location:
        """Get existing location by coordinates or create a new one."""
        try:
            # Try to get existing location
            location = await self.get_by_coordinates(latitude, longitude)
            
            if location:
                return location
                
            # Create new location
            location = Location(
                name=name,
                location_type=location_type,
                geometry=GeoPoint(coordinates=[longitude, latitude]),
                **kwargs
            )
            
            return await self.create(location)
            
        except Exception as e:
            logger.error(f"Failed to get or create location: {e}")
            raise ServiceError(
                message="Failed to get or create location",
                code="get_or_create_location_failed",
                details=str(e)
            )
