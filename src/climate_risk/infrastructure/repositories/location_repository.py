"""Location repository implementation."""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from ....domain.entities.location import Location, LocationType, GeoPoint
from ....domain.repositories import LocationRepository
from ....domain.repositories.base import FilterType, PaginationParams, SortDirection
from ..database.models import LocationModel
from .base import SQLAlchemyRepository

class LocationRepositoryImpl(
    SQLAlchemyRepository[LocationModel, Location, Location],
    LocationRepository
):
    """Location repository implementation using SQLAlchemy."""
    
    def __init__(self, session):
        """Initialize the repository."""
        super().__init__(LocationModel, session, Location)
    
    async def get_by_coordinates(
        self, 
        latitude: float, 
        longitude: float,
        radius_km: float = 10.0,
        **kwargs
    ) -> List[Location]:
        """Get locations near the given coordinates.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            radius_km: Search radius in kilometers
            **kwargs: Additional query parameters
            
        Returns:
            List of locations within the specified radius
        """
        # Convert km to degrees (approximate)
        # 1 degree ~ 111 km at the equator
        radius_deg = radius_km / 111.0
        
        # Calculate bounding box for initial filtering
        min_lat = latitude - radius_deg
        max_lat = latitude + radius_deg
        min_lon = longitude - radius_deg
        max_lon = longitude + radius_deg
        
        # Create base query
        stmt = select(self.model).where(
            and_(
                self.model.latitude.between(min_lat, max_lat),
                self.model.longitude.between(min_lon, max_lon)
            )
        )
        
        # Apply additional filters if provided
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Execute query
        result = await self.session.execute(stmt)
        locations = result.scalars().all()
        
        # Convert to domain models and filter by distance
        domain_locations = []
        for loc in locations:
            domain_loc = self.schema.from_orm(loc)
            domain_locations.append(domain_loc)
        
        return domain_locations
    
    async def search(
        self, 
        query: str,
        location_type: Optional[LocationType] = None,
        country_code: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> List[Location]:
        """Search for locations by name.
        
        Args:
            query: Search query string
            location_type: Optional location type filter
            country_code: Optional country code filter (ISO 3166-1 alpha-2)
            limit: Maximum number of results to return
            **kwargs: Additional query parameters
            
        Returns:
            List of matching locations
        """
        # Create base query with ILIKE for case-insensitive search
        stmt = select(self.model).where(
            self.model.name.ilike(f"%{query}%")
        )
        
        # Apply filters
        if location_type:
            stmt = stmt.where(self.model.location_type == location_type)
            
        if country_code:
            stmt = stmt.where(self.model.country_code == country_code.upper())
        
        # Apply limit
        stmt = stmt.limit(limit)
        
        # Execute query
        result = await self.session.execute(stmt)
        locations = result.scalars().all()
        
        # Convert to domain models
        return [self.schema.from_orm(loc) for loc in locations]
    
    async def get_by_admin_codes(
        self,
        country_code: str,
        admin1_code: Optional[str] = None,
        admin2_code: Optional[str] = None,
        admin3_code: Optional[str] = None,
        **kwargs
    ) -> List[Location]:
        """Get locations by administrative division codes.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code
            admin1_code: Admin1 code (state/region)
            admin2_code: Admin2 code (county/district)
            admin3_code: Admin3 code (municipality)
            **kwargs: Additional query parameters
            
        Returns:
            List of matching locations
        """
        # Start with country code filter
        filters = {"country_code": country_code.upper()}
        
        # Add admin codes if provided
        if admin1_code is not None:
            filters["admin1_code"] = admin1_code
            
            if admin2_code is not None:
                filters["admin2_code"] = admin2_code
                
                if admin3_code is not None:
                    filters["admin3_code"] = admin3_code
        
        # Apply any additional filters
        if "filters" in kwargs:
            filters.update(kwargs["filters"])
        
        # Get locations
        return await self.list(filters=filters, **kwargs)
    
    async def get_children(
        self, 
        parent_id: str,
        **kwargs
    ) -> List[Location]:
        """Get child locations for a parent location.
        
        Args:
            parent_id: ID of the parent location
            **kwargs: Additional query parameters
            
        Returns:
            List of child locations
        """
        # This is a simplified implementation
        # In a real application, you would need a parent-child relationship
        # in your database model
        return await self.list(filters={"parent_id": parent_id}, **kwargs)
    
    async def get_by_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        **kwargs
    ) -> List[Location]:
        """Get locations within a bounding box.
        
        Args:
            min_lat: Minimum latitude (south)
            min_lon: Minimum longitude (west)
            max_lat: Maximum latitude (north)
            max_lon: Maximum longitude (east)
            **kwargs: Additional query parameters
            
        Returns:
            List of locations within the bounding box
        """
        # Create base query with bounding box filter
        stmt = select(self.model).where(
            and_(
                self.model.latitude.between(min_lat, max_lat),
                self.model.longitude.between(min_lon, max_lon)
            )
        )
        
        # Apply additional filters if provided
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Apply pagination if provided
        if "pagination" in kwargs:
            stmt = self._apply_pagination(stmt, kwargs["pagination"])
        
        # Apply sorting if provided
        sort_by = kwargs.get("sort_by")
        sort_direction = kwargs.get("sort_direction", SortDirection.ASC)
        stmt = self._apply_sorting(stmt, sort_by, sort_direction)
        
        # Execute query
        result = await self.session.execute(stmt)
        locations = result.scalars().all()
        
        # Convert to domain models
        return [self.schema.from_orm(loc) for loc in locations]
