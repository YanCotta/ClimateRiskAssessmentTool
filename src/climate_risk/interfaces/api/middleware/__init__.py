"""
API middleware components for the Climate Risk Assessment Tool.

This module contains various middleware components that can be used to enhance
the functionality of the FastAPI application, including:

- Versioning: API versioning support
- Rate limiting: Request rate limiting
- Error handling: Centralized error handling
- Logging: Request/response logging
- Authentication: JWT authentication
- CORS: Cross-Origin Resource Sharing
"""
from .versioning import VersioningMiddleware, VersionedAPIRoute, version
from .rate_limiting import RateLimitMiddleware, RateLimitExceeded, get_rate_limiter

__all__ = [
    'VersioningMiddleware',
    'VersionedAPIRoute',
    'version',
    'RateLimitMiddleware',
    'RateLimitExceeded',
    'get_rate_limiter',
]
