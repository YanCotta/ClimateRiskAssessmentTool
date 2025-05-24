"""Repository implementations for the Climate Risk Assessment Tool."""
from typing import Dict, Type, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.repositories import (
    LocationRepository,
    WeatherDataRepository,
    RiskAssessmentRepository
)
from .location_repository import LocationRepositoryImpl
from .weather_repository import WeatherDataRepositoryImpl
from .risk_repository import RiskAssessmentRepositoryImpl

class RepositoryFactory:
    """Factory for creating repository instances."""
    
    def __init__(self, session: AsyncSession):
        """Initialize the repository factory.
        
        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._repositories: Dict[Type[Any], Any] = {}
    
    @property
    def location(self) -> LocationRepository:
        """Get the location repository."""
        if LocationRepository not in self._repositories:
            self._repositories[LocationRepository] = LocationRepositoryImpl(self._session)
        return self._repositories[LocationRepository]
    
    @property
    def weather(self) -> WeatherDataRepository:
        """Get the weather data repository."""
        if WeatherDataRepository not in self._repositories:
            self._repositories[WeatherDataRepository] = WeatherDataRepositoryImpl(self._session)
        return self._repositories[WeatherDataRepository]
    
    @property
    def risk_assessment(self) -> RiskAssessmentRepository:
        """Get the risk assessment repository."""
        if RiskAssessmentRepository not in self._repositories:
            self._repositories[RiskAssessmentRepository] = RiskAssessmentRepositoryImpl(self._session)
        return self._repositories[RiskAssessmentRepository]
    
    def get_repository(self, repo_type: Type[Any]) -> Any:
        """Get a repository by type.
        
        Args:
            repo_type: Repository interface class
            
        Returns:
            Repository instance
            
        Raises:
            ValueError: If the repository type is not supported
        """
        if repo_type == LocationRepository:
            return self.location
        elif repo_type == WeatherDataRepository:
            return self.weather
        elif repo_type == RiskAssessmentRepository:
            return self.risk_assessment
        else:
            raise ValueError(f"Unsupported repository type: {repo_type.__name__}")

__all__ = [
    'RepositoryFactory',
    'LocationRepositoryImpl',
    'WeatherDataRepositoryImpl',
    'RiskAssessmentRepositoryImpl',
]
