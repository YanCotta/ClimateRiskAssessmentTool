"""Location API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from ....domain.entities.location import Location, LocationType, GeoPoint
from ....application.services import LocationService
from ..dependencies import get_location_service
from .base import BaseRouter, PaginationParams

class LocationRouter(BaseRouter):
    """Router for location-related endpoints."""
    
    def __init__(self):
        """Initialize the location router."""
        super().__init__(prefix="/locations", tags=["locations"])
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Register location routes."""
        
        @self.router.get(
            "/",
            response_model=List[Location],
            summary="List locations"
        )
        async def list_locations(
            name: Optional[str] = None,
            location_type: Optional[LocationType] = None,
            country_code: Optional[str] = None,
            pagination: PaginationParams = Depends(),
            service: LocationService = Depends(get_location_service)
        ) -> List[Location]:
            """
            List locations with optional filtering and pagination.
            
            Args:
                name: Filter by location name (case-insensitive partial match)
                location_type: Filter by location type
                country_code: Filter by ISO 3166-1 alpha-2 country code
                pagination: Pagination parameters
                service: Injected location service
                
            Returns:
                List of matching locations
            """
            filters = {}
            if name:
                filters["name__icontains"] = name
            if location_type:
                filters["location_type"] = location_type
            if country_code:
                filters["country_code"] = country_code.upper()
                
            return await service.list(
                filters=filters or None,
                skip=(pagination.page - 1) * pagination.size,
                limit=pagination.size
            )
        
        @self.router.get(
            "/{location_id}",
            response_model=Location,
            responses={
                404: {"description": "Location not found"}
            },
            summary="Get location by ID"
        )
        async def get_location(
            location_id: str,
            service: LocationService = Depends(get_location_service)
        ) -> Location:
            """
            Get a location by its ID.
            
            Args:
                location_id: The ID of the location to retrieve
                service: Injected location service
                
            Returns:
                The requested location
                
            Raises:
                HTTPException: If the location is not found
            """
            location = await service.get_by_id(location_id)
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Location with ID {location_id} not found"
                )
            return location
        
        @self.router.get(
            "/search/nearby",
            response_model=List[Location],
            summary="Search locations near a point"
        )
        async def search_nearby_locations(
            latitude: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
            longitude: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
            radius_km: float = Query(10.0, gt=0, description="Search radius in kilometers"),
            limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
            service: LocationService = Depends(get_location_service)
        ) -> List[Location]:
            """
            Search for locations near a geographical point.
            
            Args:
                latitude: Center point latitude
                longitude: Center point longitude
                radius_km: Search radius in kilometers
                limit: Maximum number of results to return
                service: Injected location service
                
            Returns:
                List of locations within the specified radius
            """
            # This would typically use a spatial query in the repository
            # For now, we'll return an empty list as a placeholder
            return []
        
        @self.router.post(
            "/",
            response_model=Location,
            status_code=status.HTTP_201_CREATED,
            summary="Create a new location"
        )
        async def create_location(
            location: Location,
            service: LocationService = Depends(get_location_service)
        ) -> Location:
            """
            Create a new location.
            
            Args:
                location: The location data
                service: Injected location service
                
            Returns:
                The created location
            """
            return await service.create(location)
        
        @self.router.put(
            "/{location_id}",
            response_model=Location,
            responses={
                404: {"description": "Location not found"}
            },
            summary="Update a location"
        )
        async def update_location(
            location_id: str,
            location: Location,
            service: LocationService = Depends(get_location_service)
        ) -> Location:
            """
            Update an existing location.
            
            Args:
                location_id: The ID of the location to update
                location: The updated location data
                service: Injected location service
                
            Returns:
                The updated location
                
            Raises:
                HTTPException: If the location is not found
            """
            updated = await service.update(location_id, location)
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Location with ID {location_id} not found"
                )
            return updated
        
        @self.router.delete(
            "/{location_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                404: {"description": "Location not found"}
            },
            summary="Delete a location"
        )
        async def delete_location(
            location_id: str,
            service: LocationService = Depends(get_location_service)
        ) -> None:
            """
            Delete a location.
            
            Args:
                location_id: The ID of the location to delete
                service: Injected location service
                
            Raises:
                HTTPException: If the location is not found
            """
            success = await service.delete(location_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Location with ID {location_id} not found"
                )

# Create router instance
router = LocationRouter().router
