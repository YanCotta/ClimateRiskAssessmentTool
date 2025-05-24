"""Service layer for the application.

This module provides services that implement the business logic of the application,
coordinating between the domain models and the infrastructure layer.
"""
from typing import Dict, Any, Optional, Type, TypeVar

from ....domain.repositories import (
    LocationRepository,
    WeatherDataRepository,
    RiskAssessmentRepository
)
from .base import BaseService, ServiceError
from .location_service import LocationService
from .weather_service import WeatherService
from .risk_service import RiskAssessmentService

# Type variable for service classes
T = TypeVar('T', bound=BaseService)

class ServiceFactory:
    """Factory for creating and managing service instances."""
    
    def __init__(
        self,
        location_repository: LocationRepository,
        weather_repository: WeatherDataRepository,
        risk_repository: RiskAssessmentRepository
    ):
        """Initialize the service factory with required repositories."""
        self._location_repository = location_repository
        self._weather_repository = weather_repository
        self._risk_repository = risk_repository
        
        # Cache for service instances
        self._services: Dict[Type[T], T] = {}
    
    @property
    def location(self) -> LocationService:
        """Get the location service."""
        if LocationService not in self._services:
            self._services[LocationService] = LocationService(
                repository=self._location_repository
            )
        return self._services[LocationService]
    
    @property
    def weather(self) -> WeatherService:
        """Get the weather service."""
        if WeatherService not in self._services:
            self._services[WeatherService] = WeatherService(
                repository=self._weather_repository,
                location_repository=self._location_repository
            )
        return self._services[WeatherService]
    
    @property
    def risk(self) -> RiskAssessmentService:
        """Get the risk assessment service."""
        if RiskAssessmentService not in self._services:
            self._services[RiskAssessmentService] = RiskAssessmentService(
                repository=self._risk_repository,
                weather_repository=self._weather_repository,
                location_repository=self._location_repository
            )
        return self._services[RiskAssessmentService]
    
    def get_service(self, service_class: Type[T]) -> T:
        """Get a service instance by class."""
        if service_class not in self._services:
            # Try to create the service if it's not in the cache
            if service_class == LocationService:
                return self.location
            elif service_class == WeatherService:
                return self.weather
            elif service_class == RiskAssessmentService:
                return self.risk
            else:
                raise ValueError(f"Unknown service class: {service_class.__name__}")
        return self._services[service_class]

__all__ = [
    'ServiceFactory',
    'ServiceError',
    'LocationService',
    'WeatherService',
    'RiskAssessmentService',
]
