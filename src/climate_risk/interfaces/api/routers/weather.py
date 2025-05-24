"""Weather API endpoints."""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....domain.entities.weather import WeatherData
from ....application.services import WeatherService
from ..dependencies import get_weather_service

class WeatherRouter:
    """Router for weather-related endpoints."""
    
    def __init__(self):
        """Initialize the weather router."""
        self.router = APIRouter(prefix="/weather", tags=["weather"])
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Register weather routes."""
        
        @self.router.get(
            "/locations/{location_id}",
            response_model=List[WeatherData],
            summary="Get weather data for a location"
        )
        async def get_weather_for_location(
            location_id: str,
            start_date: Optional[datetime] = Query(
                None,
                description="Start date for the weather data range"
            ),
            end_date: Optional[datetime] = Query(
                None,
                description="End date for the weather data range"
            ),
            service: WeatherService = Depends(get_weather_service)
        ) -> List[WeatherData]:
            """
            Get weather data for a specific location within a date range.
            
            Args:
                location_id: The ID of the location
                start_date: Optional start date for filtering
                end_date: Optional end date for filtering
                service: Injected weather service
                
            Returns:
                List of weather data points for the location
            """
            return await service.get_for_location(
                location_id=location_id,
                start_date=start_date,
                end_date=end_date
            )
        
        @self.router.get(
            "/locations/{location_id}/current",
            response_model=WeatherData,
            summary="Get current weather for a location"
        )
        async def get_current_weather(
            location_id: str,
            service: WeatherService = Depends(get_weather_service)
        ) -> Optional[WeatherData]:
            """
            Get the current weather for a specific location.
            
            Args:
                location_id: The ID of the location
                service: Injected weather service
                
            Returns:
                Current weather data for the location, or None if not available
            """
            weather = await service.get_current_weather(location_id)
            if not weather:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No current weather data available for location {location_id}"
                )
            return weather
        
        @self.router.get(
            "/locations/{location_id}/forecast",
            response_model=List[WeatherData],
            summary="Get weather forecast for a location"
        )
        async def get_weather_forecast(
            location_id: str,
            days: int = Query(
                7,
                ge=1,
                le=14,
                description="Number of days to forecast (1-14)"
            ),
            service: WeatherService = Depends(get_weather_service)
        ) -> List[WeatherData]:
            """
            Get weather forecast for a specific location.
            
            Args:
                location_id: The ID of the location
                days: Number of days to forecast (1-14)
                service: Injected weather service
                
            Returns:
                List of forecasted weather data points
            """
            return await service.get_forecast(location_id, days=days)
        
        @self.router.get(
            "/locations/{location_id}/historical",
            response_model=List[WeatherData],
            summary="Get historical weather data for a location"
        )
        async def get_historical_weather(
            location_id: str,
            start_date: datetime = Query(
                ...,
                description="Start date for historical data"
            ),
            end_date: Optional[datetime] = Query(
                None,
                description="End date for historical data (defaults to now)"
            ),
            service: WeatherService = Depends(get_weather_service)
        ) -> List[WeatherData]:
            """
            Get historical weather data for a specific location.
            
            Args:
                location_id: The ID of the location
                start_date: Start date for the historical data
                end_date: Optional end date (defaults to now)
                service: Injected weather service
                
            Returns:
                List of historical weather data points
            """
            return await service.get_historical_weather(
                location_id=location_id,
                start_date=start_date,
                end_date=end_date
            )

# Create router instance
router = WeatherRouter().router
