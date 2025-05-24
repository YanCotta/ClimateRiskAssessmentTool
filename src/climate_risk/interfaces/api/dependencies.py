"""Dependency injection for API endpoints."""
from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.services import (
    ServiceFactory,
    LocationService,
    WeatherService,
    RiskAssessmentService,
    ServiceError
)
from ....infrastructure.database.session import AsyncSessionLocal
from ....infrastructure.repositories import (
    LocationRepositoryImpl,
    WeatherDataRepositoryImpl,
    RiskAssessmentRepositoryImpl
)

# Database session dependency
async def get_db() -> Generator:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Repository dependencies
async def get_location_repository(
    db: AsyncSession = Depends(get_db)
) -> LocationRepositoryImpl:
    """Get location repository instance."""
    return LocationRepositoryImpl(db)

async def get_weather_repository(
    db: AsyncSession = Depends(get_db)
) -> WeatherDataRepositoryImpl:
    """Get weather data repository instance."""
    return WeatherDataRepositoryImpl(db)

async def get_risk_repository(
    db: AsyncSession = Depends(get_db)
) -> RiskAssessmentRepositoryImpl:
    """Get risk assessment repository instance."""
    return RiskAssessmentRepositoryImpl(db)

# Service factory dependency
async def get_service_factory(
    location_repo: LocationRepositoryImpl = Depends(get_location_repository),
    weather_repo: WeatherDataRepositoryImpl = Depends(get_weather_repository),
    risk_repo: RiskAssessmentRepositoryImpl = Depends(get_risk_repository)
) -> ServiceFactory:
    """Get service factory with all dependencies."""
    return ServiceFactory(
        location_repository=location_repo,
        weather_repository=weather_repo,
        risk_repository=risk_repo
    )

# Individual service dependencies
async def get_location_service(
    factory: ServiceFactory = Depends(get_service_factory)
) -> LocationService:
    """Get location service instance."""
    return factory.location

async def get_weather_service(
    factory: ServiceFactory = Depends(get_service_factory)
) -> WeatherService:
    """Get weather service instance."""
    return factory.weather

async def get_risk_service(
    factory: ServiceFactory = Depends(get_service_factory)
) -> RiskAssessmentService:
    """Get risk assessment service instance."""
    return factory.risk

def handle_service_error(error: ServiceError) -> None:
    """Handle service errors and convert to HTTP exceptions."""
    status_code = status.HTTP_400_BAD_REQUEST
    
    # Map error codes to status codes
    error_code_map = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "already_exists": status.HTTP_409_CONFLICT,
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "validation_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
    }
    
    status_code = error_code_map.get(error.code, status.HTTP_400_BAD_REQUEST)
    
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": error.code or "service_error",
            "message": error.message,
            "details": error.details
        }
    )
