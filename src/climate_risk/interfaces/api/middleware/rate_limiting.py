"""Rate limiting middleware for FastAPI."""
import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, Deque, Optional, Callable, Awaitable, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import json

from fastapi import FastAPI, Request, Response, status, HTTPException
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ....config.settings import settings

class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(
        self, 
        detail: str = "Rate limit exceeded",
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers or {}
        )

class RateLimiter:
    """In-memory rate limiter implementation.
    
    This is a simple in-memory implementation. For production use, consider
    using Redis or another distributed store.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_limits: Dict[str, Tuple[int, int]] = None,
        key_func: Callable[[Request], str] = None,
        storage: str = "memory",
        redis_url: str = None,
        **kwargs
    ) -> None:
        """Initialize the rate limiter.
        
        Args:
            app: The ASGI application
            default_limits: Default rate limits in the format {"default": (requests, seconds)}
            key_func: Function to generate a key for rate limiting
            storage: Storage backend ('memory' or 'redis')
            redis_url: Redis URL (required if storage is 'redis')
        """
        self.app = app
        self.default_limits = default_limits or {"default": (100, 60)}  # 100 requests per minute by default
        self.key_func = key_func or self._default_key_func
        self.storage = storage
        self.redis_url = redis_url
        self.redis = None
        
        # In-memory storage
        self._storage: Dict[str, Deque[float]] = defaultdict(deque)
        self._cleanup_task = None
        
        # Initialize Redis if needed
        if storage == "redis":
            self._init_redis()
            
        # Start cleanup task for in-memory storage
        if storage == "memory":
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
            
        request = Request(scope, receive=receive)
        
        try:
            # Get the rate limit for this endpoint
            endpoint = request.url.path
            limits = self._get_limits_for_endpoint(endpoint)
            
            # Apply rate limiting
            for limit in limits:
                await self._check_rate_limit(request, *limit)
                
            # Process the request
            return await self.app(scope, receive, send)
            
        except RateLimitExceeded as e:
            response = Response(
                content=json.dumps({"detail": str(e.detail)}),
                status_code=e.status_code,
                headers=e.headers,
                media_type="application/json"
            )
            await response(scope, receive, send)
    
    def _get_limits_for_endpoint(self, endpoint: str) -> list:
        """Get rate limits for a specific endpoint."""
        # In a real app, you might want to configure different limits per endpoint
        return [self.default_limits.get("default", (100, 60))]
    
    async def _check_rate_limit(self, request: Request, limit: int, window: int) -> None:
        """Check if the request is allowed based on rate limits."""
        key = self.key_func(request)
        now = time.time()
        
        if self.storage == "redis":
            await self._check_redis_rate_limit(key, limit, window, now)
        else:
            await self._check_memory_rate_limit(key, limit, window, now)
    
    async def _check_memory_rate_limit(self, key: str, limit: int, window: int, timestamp: float) -> None:
        """Check rate limit using in-memory storage."""
        # Remove timestamps older than the window
        while self._storage[key] and self._storage[key][0] <= timestamp - window:
            self._storage[key].popleft()
            
        # Check if we've exceeded the limit
        if len(self._storage[key]) >= limit:
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded: {limit} requests per {window} seconds",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(self._storage[key][0] + window)),
                    "Retry-After": str(int((self._storage[key][0] + window) - timestamp))
                }
            )
            
        # Add the current timestamp
        self._storage[key].append(timestamp)
    
    async def _check_redis_rate_limit(self, key: str, limit: int, window: int, timestamp: float) -> None:
        """Check rate limit using Redis."""
        if not self.redis:
            self._init_redis()
            
        if not self.redis:
            # Fall back to in-memory if Redis is not available
            return await self._check_memory_rate_limit(key, limit, window, timestamp)
            
        try:
            # Use Redis sorted sets for rate limiting
            pipe = self.redis.pipeline()
            now = int(timestamp)
            
            # Remove old timestamps
            pipe.zremrangebyscore(key, 0, now - window)
            
            # Get current count
            pipe.zcard(key)
            
            # Add current timestamp
            pipe.zadd(key, {now: now})
            
            # Set expiry
            pipe.expire(key, window)
            
            results = await pipe.execute()
            count = results[1]  # Result of zcard
            
            if count >= limit:
                # Get the oldest timestamp to calculate reset time
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                reset_time = int(oldest[0][1] + window) if oldest else now + window
                
                raise RateLimitExceeded(
                    detail=f"Rate limit exceeded: {limit} requests per {window} seconds",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time - now)
                    }
                )
                
        except Exception as e:
            # If Redis fails, log the error but allow the request
            import logging
            logging.error(f"Redis error in rate limiting: {str(e)}")
    
    def _init_redis(self) -> None:
        """Initialize Redis client."""
        if self.storage != "redis" or not self.redis_url:
            return
            
        try:
            import redis as redis_client
            import redis.asyncio as aredis
            
            self.redis = aredis.from_url(self.redis_url)
            # Test the connection
            asyncio.create_task(self.redis.ping())
            
        except ImportError:
            import logging
            logging.warning("Redis not installed. Falling back to in-memory storage.")
            self.storage = "memory"
            
        except Exception as e:
            import logging
            logging.error(f"Failed to connect to Redis: {str(e)}. Falling back to in-memory storage.")
            self.storage = "memory"
    
    async def _cleanup_expired(self, interval: int = 300) -> None:
        """Periodically clean up expired rate limit entries."""
        while True:
            try:
                await asyncio.sleep(interval)
                now = time.time()
                
                # Create a list of keys to avoid dictionary changed size during iteration
                keys = list(self._storage.keys())
                
                for key in keys:
                    # Remove empty deques
                    if not self._storage[key]:
                        del self._storage[key]
                        
            except Exception as e:
                import logging
                logging.error(f"Error in rate limiter cleanup: {str(e)}")
    
    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Default key function for rate limiting.
        
        Creates a key based on the client IP and the endpoint.
        """
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        
        # Include query parameters in the key if needed
        if request.query_params:
            endpoint = f"{endpoint}?{request.query_params}"
            
        # Create a hash of the key components
        key = f"{client_ip}:{endpoint}"
        return hashlib.md5(key.encode()).hexdigest()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""
    
    def __init__(
        self,
        app: ASGIApp,
        default_limits: Dict[str, Tuple[int, int]] = None,
        key_func: Callable[[Request], str] = None,
        storage: str = "memory",
        redis_url: str = None,
        **kwargs
    ) -> None:
        super().__init__(app)
        self.rate_limiter = RateLimiter(
            app=app,
            default_limits=default_limits,
            key_func=key_func,
            storage=storage,
            redis_url=redis_url,
            **kwargs
        )
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            # Delegate to the rate limiter
            response = await call_next(request)
            return response
            
        except RateLimitExceeded as e:
            return Response(
                content=json.dumps({"detail": str(e.detail)}),
                status_code=e.status_code,
                headers=e.headers,
                media_type="application/json"
            )


def get_rate_limiter(
    app: FastAPI,
    default_limits: Dict[str, Tuple[int, int]] = None,
    key_func: Callable[[Request], str] = None,
    storage: str = None,
    redis_url: str = None,
    **kwargs
) -> RateLimiter:
    """Get a rate limiter instance.
    
    This is a convenience function to create and configure a rate limiter.
    """
    storage = storage or settings.RATE_LIMIT_STORAGE
    redis_url = redis_url or settings.REDIS_URL if hasattr(settings, "REDIS_URL") else None
    
    return RateLimiter(
        app=app,
        default_limits=default_limits or settings.RATE_LIMITS,
        key_func=key_func,
        storage=storage,
        redis_url=redis_url,
        **kwargs
    )
