"""Weather service implementation."""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

from ....domain.entities.weather import WeatherData, AirQuality, WeatherCondition
from ....domain.entities.location import Location
from ....domain.repositories import WeatherDataRepository, LocationRepository
from ..services.base import BaseService, ServiceError
from ....config.settings import settings

logger = logging.getLogger(__name__)

class WeatherService(BaseService[WeatherData]):
    """Service for weather-related operations."""
    
    def __init__(
        self, 
        repository: WeatherDataRepository,
        location_repository: LocationRepository
    ):
        super().__init__(repository)
        self.location_repository = location_repository
    
    async def get_for_location(
        self,
        location_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[WeatherData]:
        """Get weather data for a location within a date range."""
        try:
            return await self.repository.get_for_location(
                location_id=location_id,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to get weather data for location {location_id}: {e}")
            raise ServiceError(
                message=f"Failed to get weather data for location {location_id}",
                code="get_weather_for_location_failed",
                details=str(e)
            )
    
    async def get_latest_for_location(
        self,
        location_id: str,
        **kwargs
    ) -> Optional[WeatherData]:
        """Get the most recent weather data for a location."""
        try:
            return await self.repository.get_latest_for_location(
                location_id=location_id,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to get latest weather for location {location_id}: {e}")
            raise ServiceError(
                message=f"Failed to get latest weather for location {location_id}",
                code="get_latest_weather_failed",
                details=str(e)
            )
    
    async def get_forecast(
        self,
        location_id: str,
        days: int = 7,
        **kwargs
    ) -> List[WeatherData]:
        """Get weather forecast for a location."""
        try:
            # Check if we have a recent forecast in the database
            now = datetime.utcnow()
            forecast = await self.repository.get_for_location(
                location_id=location_id,
                start_date=now,
                end_date=now + timedelta(days=days),
                **kwargs
            )
            
            # If we have a recent forecast, return it
            if forecast and len(forecast) > 0:
                # Check if the forecast is recent enough (less than 1 hour old)
                latest = max(w.timestamp for w in forecast)
                if (now - latest).total_seconds() < 3600:  # 1 hour
                    return forecast
            
            # Otherwise, fetch from external API (implementation would go here)
            # This is a placeholder for the actual implementation
            # forecast = await self._fetch_forecast_from_api(location_id, days)
            # return await self._save_forecast(location_id, forecast)
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get forecast for location {location_id}: {e}")
            raise ServiceError(
                message=f"Failed to get forecast for location {location_id}",
                code="get_forecast_failed",
                details=str(e)
            )
    
    async def get_current_weather(
        self,
        location_id: str,
        **kwargs
    ) -> Optional[WeatherData]:
        """Get current weather for a location."""
        try:
            # Try to get from database first
            weather = await self.get_latest_for_location(location_id, **kwargs)
            
            # If data is recent (less than 10 minutes old), return it
            if weather and (datetime.utcnow() - weather.timestamp).total_seconds() < 600:
                return weather
                
            # Otherwise, fetch from external API
            # This is a placeholder for the actual implementation
            # current = await self._fetch_current_weather_from_api(location_id)
            # return await self._save_weather_data(location_id, current)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current weather for location {location_id}: {e}")
            raise ServiceError(
                message=f"Failed to get current weather for location {location_id}",
                code="get_current_weather_failed",
                details=str(e)
            )
    
    async def get_historical_weather(
        self,
        location_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[WeatherData]:
        """Get historical weather data for a location."""
        try:
            if end_date is None:
                end_date = datetime.utcnow()
                
            return await self.get_for_location(
                location_id=location_id,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to get historical weather for location {location_id}: {e}")
            raise ServiceError(
                message=f"Failed to get historical weather for location {location_id}",
                code="get_historical_weather_failed",
                details=str(e)
            )
