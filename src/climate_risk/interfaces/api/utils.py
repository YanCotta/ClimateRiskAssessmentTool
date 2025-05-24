"""Utility functions for the API layer."""
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union
from datetime import datetime, date
from enum import Enum

from fastapi import Query, HTTPException, status, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, create_model
from pydantic.generics import GenericModel
from sqlalchemy import inspect
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.entities.base import BaseEntity
from ....domain.entities.location import Location, GeoPoint
from ....domain.entities.weather import WeatherData, WeatherCondition, WeatherForecast
from ....domain.entities.risk import RiskAssessment, RiskScore, RiskLevel
from ....domain.repositories.base import FilterType, SortDirection, PaginationParams as BasePaginationParams
from ....infrastructure.database.session import get_db as get_db_session

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic types
T = TypeVar('T')

class ResponseModel(GenericModel, Generic[T]):
    """Generic response model for API responses."""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if any")
    meta: Optional[Dict[str, Any]] = Field(None, description="Metadata about the response")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Enum: lambda v: v.value,
        }
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "error": None,
                "meta": {}
            }
        }

    @classmethod
    def success(
        cls,
        data: Optional[T] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> 'ResponseModel[T]':
        """Create a successful response."""
        return cls(success=True, data=data, error=None, meta=meta or {})

    @classmethod
    def error(
        cls,
        message: str,
        code: str = "error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ) -> 'ResponseModel[None]':
        """Create an error response."""
        error_info = {
            "message": message,
            "code": code,
            "status_code": status_code,
        }
        if details:
            error_info["details"] = details
        
        return cls(success=False, data=None, error=error_info, meta={})

def create_response(
    data: Any = None,
    status_code: int = status.HTTP_200_OK,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standardized API response.
    
    Args:
        data: The data to include in the response
        status_code: The HTTP status code
        meta: Additional metadata to include
        
    Returns:
        Dict containing the response data
    """
    response = {
        "success": status_code < 400,
        "data": data,
    }
    
    if meta:
        response["meta"] = meta
    
    return jsonable_encoder(response)

def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
) -> BasePaginationParams:
    """Get pagination parameters from query string."""
    return BasePaginationParams(skip=skip, limit=limit)

async def get_entity_or_404(
    entity_id: str,
    repository: Any,
    session: AsyncSession,
    entity_name: str = "Resource",
) -> Any:
    """Get an entity by ID or raise a 404 error.
    
    Args:
        entity_id: The ID of the entity to retrieve
        repository: The repository to use for the query
        session: The database session
        entity_name: The name of the entity for error messages
        
    Returns:
        The requested entity
        
    Raises:
        HTTPException: If the entity is not found
    """
    entity = await repository.get_by_id(session, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} with ID {entity_id} not found",
        )
    return entity

def validate_location(location_data: Dict[str, Any]) -> Location:
    """Validate and create a Location object from request data."""
    try:
        return Location(**location_data)
    except Exception as e:
        logger.error(f"Invalid location data: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid location data: {str(e)}",
        )

def validate_weather_data(weather_data: Dict[str, Any]) -> WeatherData:
    """Validate and create a WeatherData object from request data."""
    try:
        return WeatherData(**weather_data)
    except Exception as e:
        logger.error(f"Invalid weather data: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid weather data: {str(e)}",
        )

def validate_risk_assessment(assessment_data: Dict[str, Any]) -> RiskAssessment:
    """Validate and create a RiskAssessment object from request data."""
    try:
        return RiskAssessment(**assessment_data)
    except Exception as e:
        logger.error(f"Invalid risk assessment data: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid risk assessment data: {str(e)}",
        )

def apply_filters(
    query: Any,
    model: Type[BaseEntity],
    filters: Optional[Dict[str, Any]] = None,
) -> Any:
    """Apply filters to a SQLAlchemy query.
    
    Args:
        query: The SQLAlchemy query to filter
        model: The SQLAlchemy model class
        filters: Dictionary of filters to apply
        
    Returns:
        The filtered query
    """
    if not filters:
        return query
    
    # Get the model's column names
    mapper = inspect(model)
    column_names = {column.name for column in mapper.columns}
    
    # Apply filters
    for field, value in filters.items():
        if field not in column_names:
            continue
            
        column = getattr(model, field)
        if isinstance(value, (list, tuple, set)):
            query = query.filter(column.in_(value))
        elif isinstance(value, dict):
            for op, op_value in value.items():
                if op == "eq":
                    query = query.filter(column == op_value)
                elif op == "ne":
                    query = query.filter(column != op_value)
                elif op == "gt":
                    query = query.filter(column > op_value)
                elif op == "lt":
                    query = query.filter(column < op_value)
                elif op == "ge":
                    query = query.filter(column >= op_value)
                elif op == "le":
                    query = query.filter(column <= op_value)
                elif op == "like":
                    query = query.filter(column.like(f"%{op_value}%"))
                elif op == "ilike":
                    query = query.filter(column.ilike(f"%{op_value}%"))
                elif op == "in":
                    query = query.filter(column.in_(op_value))
                elif op == "not_in":
                    query = query.filter(~column.in_(op_value))
                elif op == "is_null":
                    if op_value:
                        query = query.filter(column.is_(None))
                    else:
                        query = query.filter(column.isnot(None))
        else:
            query = query.filter(column == value)
    
    return query

def apply_sorting(
    query: Any,
    model: Type[BaseEntity],
    sort_by: Optional[str] = None,
    sort_direction: SortDirection = SortDirection.ASC,
) -> Any:
    """Apply sorting to a SQLAlchemy query.
    
    Args:
        query: The SQLAlchemy query to sort
        model: The SQLAlchemy model class
        sort_by: The field to sort by
        sort_direction: The sort direction (ascending or descending)
        
    Returns:
        The sorted query
    """
    if not sort_by:
        return query
    
    # Get the model's column names
    mapper = inspect(model)
    column_names = {column.name for column in mapper.columns}
    
    # Apply sorting
    if sort_by in column_names:
        column = getattr(model, sort_by)
        if sort_direction == SortDirection.DESC:
            return query.order_by(column.desc())
        return query.order_by(column.asc())
    
    return query

def apply_pagination(
    query: Any,
    pagination: BasePaginationParams,
) -> Any:
    """Apply pagination to a SQLAlchemy query.
    
    Args:
        query: The SQLAlchemy query to paginate
        pagination: The pagination parameters
        
    Returns:
        The paginated query
    """
    if pagination.skip > 0:
        query = query.offset(pagination.skip)
    if pagination.limit is not None:
        query = query.limit(pagination.limit)
    return query

def get_entity_filters(
    model: Type[BaseEntity],
    **filters: Any,
) -> Dict[str, Any]:
    """Get valid filters for an entity model.
    
    Args:
        model: The SQLAlchemy model class
        **filters: The filters to validate
        
    Returns:
        A dictionary of valid filters
    """
    if not filters:
        return {}
    
    # Get the model's column names
    mapper = inspect(model)
    column_names = {column.name for column in mapper.columns}
    
    # Filter out invalid columns
    return {k: v for k, v in filters.items() if k in column_names}

async def get_db_connection() -> AsyncSession:
    """Get a database connection."""
    async with get_db_session() as session:
        try:
            yield session
        finally:
            await session.close()
