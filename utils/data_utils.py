import numpy as np
from typing import List, Dict
from datetime import datetime
from ..Core.model_training import WeatherData
from .logging_utils import get_logger  # Added import

logger = get_logger(__name__)  # Initialized logger

def validate_weather_data(data: WeatherData) -> bool:
    """Validate weather data measurements"""
    return (
        -100 <= data.temperature <= 60 and  # Valid temperature range
        0 <= data.precipitation <= 2000 and  # Valid precipitation range
        0 <= data.humidity <= 100 and  # Valid humidity range
        0 <= data.wind_speed <= 500 and  # Valid wind speed range
        800 <= data.pressure <= 1100  # Valid pressure range
    )

def transform_weather_data_to_features(weather_data: List<WeatherData]) -> np.ndarray:
    """Transform weather data to feature matrix for model input"""
    return np.array([w.to_feature_vector() for w in weather_data])

def merge_weather_data(api_results: List<Dict]) -> List<WeatherData]:
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
            if validate_weather_data(weather_data):
                merged_data.append(weather_data)
        except Exception as e:
            logger.error(f"Data merge failed: {e}")  # Now properly logged
            continue
    
    return merged_data
