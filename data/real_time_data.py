import logging
import aiohttp
import asyncio
from typing import List, Dict
from datetime import datetime
from dataclasses import dataclass
from ..Core.model_training import WeatherData, Location
from ..Core.data_integration import DataIntegration, APIConfig

logger = logging.getLogger(__name__)

@dataclass
class RealTimeAPIConfig(APIConfig):
    """Configuration for real-time weather data APIs"""
    update_interval: int = 10  # minutes

class RealTimeDataFetcher:
    def __init__(self, config: Dict[str, RealTimeAPIConfig]):
        self.config = config
        self.data_integration = DataIntegration(config)
        self._session = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        await self.data_integration.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
        await self.data_integration.__aexit__(exc_type, exc_val, exc_tb)

    async def fetch_real_time_data(self, location: Location) -> List[WeatherData]:
        """Fetch real-time weather data"""
        try:
            return await self.data_integration.fetch_weather_data(location)
        except Exception as e:
            logger.error(f"Real-time data fetch failed: {e}")
            return []

    async def start_real_time_updates(self, location: Location, callback):
        """Start fetching real-time updates at regular intervals"""
        while True:
            weather_data = await self.fetch_real_time_data(location)
            callback(weather_data)
            await asyncio.sleep(self.config['weather_api'].update_interval * 60)
