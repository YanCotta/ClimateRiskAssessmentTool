"""Weather data repository implementation."""
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, or_, between
from sqlalchemy.orm import selectinload, joinedload

from ....domain.entities.weather import WeatherData, WeatherCondition, WeatherForecast, WeatherHistory
from ....domain.entities.location import GeoPoint
from ....domain.repositories import WeatherDataRepository
from ....domain.repositories.base import FilterType, PaginationParams, SortDirection
from ..database.models import WeatherDataModel, LocationModel
from .base import SQLAlchemyRepository

class WeatherDataRepositoryImpl(
    SQLAlchemyRepository[WeatherDataModel, WeatherData, WeatherData],
    WeatherDataRepository
):
    """Weather data repository implementation using SQLAlchemy."""
    
    def __init__(self, session):
        """Initialize the repository."""
        super().__init__(WeatherDataModel, session, WeatherData)
    
    async def get_for_location(
        self, 
        location_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[WeatherData]:
        """Get weather data for a specific location and time range.
        
        Args:
            location_id: Location ID
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            **kwargs: Additional query parameters
            
        Returns:
            List of weather data points
        """
        # Create base query
        stmt = select(self.model).where(
            self.model.location_id == location_id
        )
        
        # Apply date range filter if provided
        if start_date and end_date:
            stmt = stmt.where(
                between(self.model.timestamp, start_date, end_date)
            )
        elif start_date:
            stmt = stmt.where(self.model.timestamp >= start_date)
        elif end_date:
            stmt = stmt.where(self.model.timestamp <= end_date)
        
        # Apply additional filters if provided
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Apply sorting (newest first by default)
        sort_by = kwargs.get("sort_by", "timestamp")
        sort_direction = kwargs.get("sort_direction", SortDirection.DESC)
        stmt = self._apply_sorting(stmt, sort_by, sort_direction)
        
        # Apply pagination if provided
        if "pagination" in kwargs:
            stmt = self._apply_pagination(stmt, kwargs["pagination"])
        
        # Execute query
        result = await self.session.execute(stmt)
        weather_data = result.scalars().all()
        
        # Convert to domain models
        return [self.schema.from_orm(data) for data in weather_data]
    
    async def get_current_weather(
        self, 
        location_id: str,
        **kwargs
    ) -> Optional[WeatherData]:
        """Get the current weather for a location.
        
        Args:
            location_id: Location ID
            **kwargs: Additional query parameters
            
        Returns:
            Current weather data if available, None otherwise
        """
        # Get the most recent weather data for the location
        stmt = select(self.model).where(
            self.model.location_id == location_id
        ).order_by(
            self.model.timestamp.desc()
        ).limit(1)
        
        # Execute query
        result = await self.session.execute(stmt)
        weather_data = result.scalars().first()
        
        if not weather_data:
            return None
            
        return self.schema.from_orm(weather_data)
    
    async def get_forecast(
        self, 
        location_id: str,
        days: int = 7,
        **kwargs
    ) -> List[WeatherData]:
        """Get weather forecast for a location.
        
        Args:
            location_id: Location ID
            days: Number of days to forecast (default: 7)
            **kwargs: Additional query parameters
            
        Returns:
            List of forecasted weather data points
        """
        # Calculate date range
        now = datetime.utcnow()
        start_date = now
        end_date = now + timedelta(days=days)
        
        # Get forecast data from the database
        # Note: In a real application, you would typically call a weather API here
        # and then store the results in the database
        stmt = select(self.model).where(
            and_(
                self.model.location_id == location_id,
                self.model.timestamp >= start_date,
                self.model.timestamp <= end_date
            )
        ).order_by(self.model.timestamp.asc())
        
        # Execute query
        result = await self.session.execute(stmt)
        forecast_data = result.scalars().all()
        
        # Convert to domain models
        return [self.schema.from_orm(data) for data in forecast_data]
    
    async def get_historical_weather(
        self, 
        location_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[WeatherData]:
        """Get historical weather data for a location.
        
        Args:
            location_id: Location ID
            start_date: Start date for historical data
            end_date: Optional end date (defaults to now)
            **kwargs: Additional query parameters
            
        Returns:
            List of historical weather data points
        """
        # Set default end date to now if not provided
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Get historical data from the database
        stmt = select(self.model).where(
            and_(
                self.model.location_id == location_id,
                self.model.timestamp >= start_date,
                self.model.timestamp <= end_date
            )
        ).order_by(self.model.timestamp.asc())
        
        # Apply additional filters if provided
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Apply pagination if provided
        if "pagination" in kwargs:
            stmt = self._apply_pagination(stmt, kwargs["pagination"])
        
        # Execute query
        result = await self.session.execute(stmt)
        historical_data = result.scalars().all()
        
        # Convert to domain models
        return [self.schema.from_orm(data) for data in historical_data]
    
    async def get_stats(
        self,
        location_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get weather statistics for a location and time period.
        
        Args:
            location_id: Location ID
            start_date: Start date for statistics
            end_date: Optional end date (defaults to now)
            **kwargs: Additional query parameters
            
        Returns:
            Dictionary containing weather statistics
        """
        # Set default end date to now if not provided
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Create base query
        stmt = select([
            func.avg(self.model.temperature).label("avg_temperature"),
            func.max(self.model.temperature).label("max_temperature"),
            func.min(self.model.temperature).label("min_temperature"),
            func.avg(self.model.humidity).label("avg_humidity"),
            func.sum(self.model.precipitation).label("total_precipitation"),
            func.avg(self.model.wind_speed).label("avg_wind_speed"),
            func.max(self.model.wind_gust).label("max_wind_gust"),
        ]).where(
            and_(
                self.model.location_id == location_id,
                self.model.timestamp >= start_date,
                self.model.timestamp <= end_date
            )
        )
        
        # Apply additional filters if provided
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Execute query
        result = await self.session.execute(stmt)
        stats = result.first()
        
        # Format results
        return {
            "avg_temperature": stats.avg_temperature,
            "max_temperature": stats.max_temperature,
            "min_temperature": stats.min_temperature,
            "avg_humidity": stats.avg_humidity,
            "total_precipitation": stats.total_precipitation or 0.0,
            "avg_wind_speed": stats.avg_wind_speed,
            "max_wind_gust": stats.max_wind_gust,
            "start_date": start_date,
            "end_date": end_date,
            "location_id": location_id
        }
    
    async def bulk_create(
        self, 
        weather_data_list: List[WeatherData],
        **kwargs
    ) -> int:
        """Bulk create weather data records.
        
        Args:
            weather_data_list: List of weather data objects to create
            **kwargs: Additional parameters
            
        Returns:
            Number of records created
        """
        if not weather_data_list:
            return 0
            
        # Convert domain models to database models
        db_objects = [
            self.model(**data.dict(exclude_unset=True))
            for data in weather_data_list
        ]
        
        # Add all to session
        self.session.add_all(db_objects)
        
        try:
            await self.session.commit()
            return len(db_objects)
        except Exception as e:
            await self.session.rollback()
            raise e
