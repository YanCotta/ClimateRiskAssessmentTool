"""Climate Risk Assessment domain models and business logic."""

# Export key domain models and types
from .entities.base import BaseEntity, PaginatedResponse
from .entities.location import Location, LocationType, GeoPoint
from .entities.weather import WeatherData, WeatherCondition, AirQuality
from .entities.risk import (
    RiskScore, 
    RiskAssessment, 
    RiskLevel, 
    RiskType
)

__all__ = [
    # Base
    'BaseEntity',
    'PaginatedResponse',
    
    # Location
    'Location',
    'LocationType',
    'GeoPoint',
    
    # Weather
    'WeatherData',
    'WeatherCondition',
    'AirQuality',
    
    # Risk
    'RiskScore',
    'RiskAssessment',
    'RiskLevel',
    'RiskType',
]
