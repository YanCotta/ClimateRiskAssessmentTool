"""Dependency injection for API endpoints."""
import logging
from typing import Generator, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

from fastapi import Depends, HTTPException, status, Request, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.services import (
    ServiceFactory,
    LocationService,
    WeatherService,
    RiskAssessmentService,
    ServiceError,
    UserService,
    AuthService,
)
from ....config.settings import settings
from ....domain.entities.user import User, UserRole
from ....infrastructure.database.session import (
    AsyncSessionLocal,
    get_db as get_db_session,
)
from ....infrastructure.repositories import (
    RepositoryFactory,
    LocationRepositoryImpl,
    WeatherDataRepositoryImpl,
    RiskAssessmentRepositoryImpl,
    UserRepositoryImpl,
)

# Configure logging
logger = logging.getLogger(__name__)

# Security schemes
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API key header for machine-to-machine authentication",
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/token",
    auto_error=False,
    scopes={
        "user:read": "Read access to user data",
        "user:write": "Write access to user data",
        "locations:read": "Read access to location data",
        "locations:write": "Write access to location data",
        "weather:read": "Read access to weather data",
        "risk:read": "Read access to risk assessments",
        "risk:write": "Write access to risk assessments",
    },
)

# Database session dependency
async def get_db() -> Generator[AsyncSession, None, None]:
    """Get database session.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        HTTPException: If there's an error with the database session
    """
    async with get_db_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            )

# Repository factory dependency
async def get_repository_factory(
    db: AsyncSession = Depends(get_db),
) -> RepositoryFactory:
    """Get repository factory with all dependencies."""
    return RepositoryFactory(session=db)

# Repository dependencies
async def get_location_repository(
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
) -> LocationRepositoryImpl:
    """Get location repository instance."""
    return repo_factory.location

async def get_weather_repository(
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
) -> WeatherDataRepositoryImpl:
    """Get weather data repository instance."""
    return repo_factory.weather

async def get_risk_repository(
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
) -> RiskAssessmentRepositoryImpl:
    """Get risk assessment repository instance."""
    return repo_factory.risk_assessment

async def get_user_repository(
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
) -> UserRepositoryImpl:
    """Get user repository instance."""
    return repo_factory.user

# Service factory dependency
async def get_service_factory(
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
) -> ServiceFactory:
    """Get service factory with all dependencies."""
    return ServiceFactory(
        location_repository=repo_factory.location,
        weather_repository=repo_factory.weather,
        risk_repository=repo_factory.risk_assessment,
        user_repository=repo_factory.user,
    )

# Individual service dependencies
async def get_location_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> LocationService:
    """Get location service instance."""
    return factory.location

async def get_weather_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> WeatherService:
    """Get weather service instance."""
    return factory.weather

async def get_risk_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> RiskAssessmentService:
    """Get risk assessment service instance."""
    return factory.risk

async def get_user_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> UserService:
    """Get user service instance."""
    return factory.user

async def get_auth_service(
    user_service: UserService = Depends(get_user_service),
) -> AuthService:
    """Get auth service instance."""
    return AuthService(user_service=user_service)

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

# Security dependencies
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Get the current authenticated user from the JWT token.
    
    Args:
        token: JWT token from the Authorization header
        auth_service: Auth service instance
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: If the token is invalid or the user is not found
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    
    user = await auth_service.get_user_by_username(username=username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active user.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        User: The active user
        
    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active superuser.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        User: The active superuser
        
    Raises:
        HTTPException: If the user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user

def has_required_roles(required_roles: list[UserRole]) -> callable:
    """Check if the current user has the required roles.
    
    Args:
        required_roles: List of required roles
        
    Returns:
        callable: Dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    
    return role_checker

# Common role-based dependencies
async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get the current admin user."""
    if UserRole.ADMIN not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user

async def get_analyst_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get the current analyst user."""
    if UserRole.ANALYST not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst access required",
        )
    return current_user

# API key authentication
def get_api_key(
    api_key: str = Depends(api_key_header),
) -> str:
    """Validate API key.
    
    Args:
        api_key: API key from the header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: If the API key is invalid
    """
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key

# Error handling
def handle_service_error(error: ServiceError) -> None:
    """Handle service errors and convert to HTTP exceptions.
    
    Args:
        error: The service error to handle
        
    Raises:
        HTTPException: The corresponding HTTP exception
    """
    # Map error codes to status codes
    error_code_map = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "already_exists": status.HTTP_409_CONFLICT,
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "validation_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "rate_limit_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
        "service_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
        "bad_request": status.HTTP_400_BAD_REQUEST,
    }
    
    status_code = error_code_map.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Log the error
    logger.error(
        f"Service error: {error.code} - {error}",
        extra={"details": error.details},
    )
    
    # Raise the appropriate HTTP exception
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": error.code,
            "message": str(error),
            "details": error.details,
        },
    )

# Pagination dependency
class PaginationParams:
    """Pagination parameters for API endpoints."""
    
    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> None:
        """Initialize pagination parameters.
        
        Args:
            skip: Number of items to skip
            limit: Maximum number of items to return
        """
        self.skip = max(0, skip)
        self.limit = min(100, max(1, limit))  # Enforce a reasonable limit

    @classmethod
    async def from_request(
        cls,
        request: Request,
        skip: int = 0,
        limit: int = 100,
    ) -> 'PaginationParams':
        """Create pagination parameters from a request.
        
        Args:
            request: The incoming request
            skip: Default number of items to skip
            limit: Default maximum number of items to return
            
        Returns:
            PaginationParams: The pagination parameters
        """
        query_params = request.query_params
        
        try:
            skip = int(query_params.get("skip", skip))
            limit = int(query_params.get("limit", limit))
        except (TypeError, ValueError):
            # Use defaults if parsing fails
            pass
            
        return cls(skip=skip, limit=limit)
