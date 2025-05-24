"""Weather-related domain entities."""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
from pydantic import Field, validator, model_validator

from .base import BaseEntity

class WeatherCondition(str, Enum):
    """Enumeration of possible weather conditions."""
    CLEAR = "clear"
    CLOUDS = "clouds"
    RAIN = "rain"
    SNOW = "snow"
    THUNDERSTORM = "thunderstorm"
    DRIZZLE = "drizzle"
    MIST = "mist"
    SMOKE = "smoke"
    HAZE = "haze"
    DUST = "dust"
    FOG = "fog"
    SAND = "sand"
    ASH = "ash"
    SQUALL = "squall"
    TORNADO = "tornado"

class AirQuality(BaseEntity):
    """Air quality metrics."""
    aqi: int = Field(..., description="Air Quality Index (0-500)", ge=0, le=500)
    co: Optional[float] = Field(None, description="Carbon Monoxide (μg/m³)")
    no2: Optional[float] = Field(None, description="Nitrogen Dioxide (μg/m³)")
    o3: Optional[float] = Field(None, description="Ozone (μg/m³)")
    so2: Optional[float] = Field(None, description="Sulphur Dioxide (μg/m³)")
    pm2_5: Optional[float] = Field(None, description="PM2.5 (μg/m³)", alias="pm2_5")
    pm10: Optional[float] = Field(None, description="PM10 (μg/m³)")
    nh3: Optional[float] = Field(None, description="Ammonia (μg/m³)")

class WeatherData(BaseEntity):
    """Weather data point with comprehensive metrics."""
    timestamp: datetime = Field(..., description="Timestamp of the data point")
    location_id: str = Field(..., description="Reference to location")
    
    # Core weather metrics
    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: Optional[float] = Field(None, description="Apparent temperature in Celsius")
    pressure: float = Field(..., description="Atmospheric pressure in hPa")
    humidity: float = Field(..., description="Humidity percentage (0-100%)", ge=0, le=100)
    dew_point: Optional[float] = Field(None, description="Dew point in Celsius")
    
    # Wind
    wind_speed: float = Field(..., description="Wind speed in m/s", ge=0)
    wind_gust: Optional[float] = Field(None, description="Wind gust in m/s", ge=0)
    wind_deg: Optional[int] = Field(None, description="Wind direction in degrees (0-360)", ge=0, le=360)
    
    # Precipitation
    rain_1h: Optional[float] = Field(None, description="Rain volume for last hour in mm", ge=0)
    snow_1h: Optional[float] = Field(None, description="Snow volume for last hour in mm", ge=0)
    
    # Clouds and visibility
    clouds: Optional[int] = Field(None, description="Cloudiness percentage (0-100%)", ge=0, le=100)
    visibility: Optional[int] = Field(None, description="Visibility in meters", ge=0)
    
    # Additional metrics
    uv_index: Optional[float] = Field(None, description="UV Index", ge=0)
    weather_condition: Optional[WeatherCondition] = Field(None, description="Current weather condition")
    air_quality: Optional[AirQuality] = Field(None, description="Air quality metrics")
    
    # Source and metadata
    source: str = Field("api", description="Data source")
    source_id: Optional[str] = Field(None, description="ID from the source system")
    
    @validator('timestamp', pre=True)
    def parse_timestamp(cls, v):
        """Parse timestamp from various formats."""
        if isinstance(v, str):
            try:
                # Try ISO format
                from dateutil.parser import isoparse
                return isoparse(v)
            except ValueError:
                # Try Unix timestamp
                try:
                    return datetime.fromtimestamp(int(v))
                except (ValueError, TypeError):
                    pass
        return v
    
    @model_validator(mode='after')
    def calculate_feels_like(self):
        """Calculate 'feels_like' temperature if not provided."""
        if self.feels_like is None and self.temperature is not None and self.humidity is not None and self.wind_speed is not None:
            # Simple wind chill and heat index calculation
            if self.temperature <= 10 and self.wind_speed > 4.8:
                # Wind chill calculation for temperatures <= 10°C and wind > 4.8 m/s
                self.feels_like = 13.12 + 0.6215 * self.temperature - 11.37 * (self.wind_speed * 3.6) ** 0.16 + 0.3965 * self.temperature * (self.wind_speed * 3.6) ** 0.16
            elif self.temperature >= 27 and self.humidity >= 40:
                # Heat index calculation for temperatures >= 27°C and humidity >= 40%
                c1 = -8.78469475556
                c2 = 1.61139411
                c3 = 2.33854883889
                c4 = -0.14611605
                c5 = -0.012308094
                c6 = -0.0164248277778
                c7 = 0.002211732
                c8 = 0.00072546
                c9 = -0.000003582
                
                t = self.temperature
                r = self.humidity
                
                hi = (c1 + c2 * t + c3 * r + c4 * t * r + 
                      c5 * t**2 + c6 * r**2 + c7 * t**2 * r + 
                      c8 * t * r**2 + c9 * t**2 * r**2)
                self.feels_like = hi
            else:
                self.feels_like = self.temperature
        return self
