import logging
import aiohttp
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass

from .model_training import WeatherData, Location

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """Configuration for weather data APIs"""
    base_url: str
    api_key: str
    endpoints: Dict[str, str]
    rate_limit: int = 60  # requests per minute

class DataIntegration:
    def __init__(self, config: Dict[str, APIConfig]):
        self.config = config
        self._session = None
        self._rate_limiters = {
            name: asyncio.Semaphore(cfg.rate_limit) 
            for name, cfg in config.items()
        }

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def fetch_weather_data(self, location: Location, days: int = 7) -> List[WeatherData]:
        """Fetch weather data from multiple sources asynchronously"""
        try:
            tasks = []
            for api_name, config in self.config.items():
                tasks.append(self._fetch_from_api(api_name, config, location, days))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return self._merge_weather_data(results)
            
        except Exception as e:
            logger.error(f"Weather data fetch failed: {e}")
            return []

    async def _fetch_from_api(self, api_name: str, config: APIConfig, 
                            location: Location, days: int) -> List[Dict]:
        """Fetch data from a single API with rate limiting"""
        async with self._rate_limiters[api_name]:
            try:
                params = {
                    'lat': location.latitude,
                    'lon': location.longitude,
                    'days': days,
                    'key': config.api_key
                }
                async with self._session.get(
                    f"{config.base_url}/forecast",
                    params=params
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            except Exception as e:
                logger.error(f"API {api_name} fetch failed: {e}")
                return []

    def _merge_weather_data(self, api_results: List[Dict]) -> List[WeatherData]:
        """Merge and validate data from multiple sources"""
        merged_data = []
        for result in api_results:
            if not result:
                continue
            try:
                weather_data = WeatherData(
                    temperature=result.get('temp', 0),
                    precipitation=result.get('precip', 0),
                    humidity=result.get('humidity', 0),
                    wind_speed=result.get('wind_speed', 0),
                    pressure=result.get('pressure', 0),
                    timestamp=datetime.fromtimestamp(result.get('ts', 0)),
                    uv_index=result.get('uv', 0),
                    air_quality=result.get('air_quality', {})
                )
                if self._validate_weather_data(weather_data):
                    merged_data.append(weather_data)
            except Exception as e:
                logger.error(f"Data merge failed: {e}")
                continue
        
        return merged_data

    def _validate_weather_data(self, data: WeatherData) -> bool:
        """Validate weather data measurements"""
        return (
            -100 <= data.temperature <= 60 and  # Valid temperature range
            0 <= data.precipitation <= 2000 and  # Valid precipitation range
            0 <= data.humidity <= 100 and  # Valid humidity range
            0 <= data.wind_speed <= 500 and  # Valid wind speed range
            800 <= data.pressure <= 1100  # Valid pressure range
        )

    async def get_historical_data(self, location: Location, 
                                start_date: datetime,
                                end_date: datetime) -> pd.DataFrame:
        """Fetch historical weather data"""
        # Implementation for historical data fetching
        pass
