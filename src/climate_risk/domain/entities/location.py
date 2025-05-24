"""Location-related domain entities."""
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import Field, validator, model_validator, HttpUrl
from datetime import datetime
import uuid

from .base import BaseEntity

class LocationType(str, Enum):
    """Type of location."""
    CITY = "city"
    REGION = "region"
    COUNTRY = "country"
    CONTINENT = "continent"
    CUSTOM = "custom"

class GeoPoint(BaseEntity):
    """Geographical point with latitude and longitude."""
    type: str = "Point"
    coordinates: List[float] = Field(..., min_items=2, max_items=2)
    
    @validator('coordinates')
    def validate_coordinates(cls, v):
        """Validate latitude and longitude values."""
        if len(v) != 2:
            raise ValueError("Coordinates must be [longitude, latitude]")
        
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        
        return v
    
    @property
    def longitude(self) -> float:
        """Get longitude."""
        return self.coordinates[0]
    
    @property
    def latitude(self) -> float:
        """Get latitude."""
        return self.coordinates[1]
    
    def to_geojson(self) -> Dict[str, Any]:
        """Convert to GeoJSON format."""
        return {
            "type": self.type,
            "coordinates": self.coordinates
        }

class Location(BaseEntity):
    """A geographical location with associated metadata."""
    
    # Core location data
    name: str = Field(..., description="Location name")
    location_type: LocationType = Field(..., description="Type of location")
    
    # Geographical data
    geometry: GeoPoint = Field(..., description="Geographical point")
    elevation: Optional[float] = Field(None, description="Elevation in meters")
    
    # Administrative data
    country_code: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code")
    admin1_code: Optional[str] = Field(None, description="Primary administrative division code")
    admin2_code: Optional[str] = Field(None, description="Secondary administrative division code")
    timezone: Optional[str] = Field(None, description="IANA timezone name")
    
    # External references
    external_ids: Dict[str, str] = Field(
        default_factory=dict,
        description="External identifiers (e.g., from weather APIs, geocoding services)"
    )
    
    # Metadata
    population: Optional[int] = Field(None, description="Population count", ge=0)
    area_km2: Optional[float] = Field(None, description="Area in square kilometers", gt=0)
    
    # Relationships
    parent_id: Optional[str] = Field(None, description="Parent location ID")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional location metadata"
    )
    
    @property
    def latitude(self) -> float:
        """Get latitude."""
        return self.geometry.latitude
    
    @property
    def longitude(self) -> float:
        """Get longitude."""
        return self.geometry.longitude
    
    @property
    def coordinates(self) -> List[float]:
        """Get coordinates as [longitude, latitude]."""
        return self.geometry.coordinates
    
    def to_geojson(self) -> Dict[str, Any]:
        """Convert to GeoJSON Feature format."""
        return {
            "type": "Feature",
            "geometry": self.geometry.to_geojson(),
            "properties": {
                "id": str(self.id),
                "name": self.name,
                "type": self.location_type,
                "country_code": self.country_code,
                "admin1_code": self.admin1_code,
                "admin2_code": self.admin2_code,
                "timezone": self.timezone,
                "elevation": self.elevation,
                "population": self.population,
                "area_km2": self.area_km2,
                "parent_id": self.parent_id,
                "external_ids": self.external_ids,
                "metadata": self.metadata,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            }
        }
    
    @classmethod
    def create_point(cls, longitude: float, latitude: float, **kwargs) -> 'Location':
        """Create a location from coordinates."""
        return cls(
            geometry=GeoPoint(coordinates=[longitude, latitude]),
            **kwargs
        )
