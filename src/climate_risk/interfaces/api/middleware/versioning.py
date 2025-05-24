"""API versioning middleware for FastAPI."""
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.routing import APIRoute
from typing import Callable, Optional, Dict, Any, List, Tuple
import re
from enum import Enum

class VersioningScheme(str, Enum):
    URL = "url"
    HEADER = "header"
    QUERY = "query"
    COOKIE = "cookie"

class VersionedAPIRoute(APIRoute):
    """Custom route class for API versioning."""
    
    def __init__(
        self,
        *args,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None,
        deprecated: bool = False,
        **kwargs
    ) -> None:
        self.min_version = min_version
        self.max_version = max_version
        self.deprecated = deprecated
        super().__init__(*args, **kwargs)

def version(
    min_version: Optional[str] = None,
    max_version: Optional[str] = None,
    deprecated: bool = False
):
    """Decorator to specify API version requirements for a route.
    
    Args:
        min_version: Minimum API version required (inclusive)
        max_version: Maximum API version supported (inclusive)
        deprecated: Whether this endpoint is deprecated
    """
    def decorator(func):
        func._min_version = min_version
        func._max_version = max_version
        func._deprecated = deprecated
        return func
    return decorator

class VersioningMiddleware:
    """Middleware for API versioning.
    
    Supports multiple versioning schemes:
    - URL path versioning (/v1/resource)
    - Header versioning (Accept: application/vnd.api.v1+json)
    - Query parameter versioning (?version=1.0)
    - Cookie versioning
    """
    
    def __init__(
        self,
        app: FastAPI,
        default_version: str = "1.0",
        version_param: str = "version",
        version_header: str = "Accept",
        version_cookie: str = "api-version",
        version_regex: str = r"^v(\d+(\.\d+)*)$",
        schemes: List[Tuple[VersioningScheme, float]] = [
            (VersioningScheme.URL, 1.0),
            (VersioningScheme.HEADER, 0.9),
            (VersioningScheme.QUERY, 0.8),
            (VersioningScheme.COOKIE, 0.7),
        ]
    ) -> None:
        self.app = app
        self.default_version = default_version
        self.version_param = version_param
        self.version_header = version_header
        self.version_cookie = version_cookie
        self.version_regex = re.compile(version_regex)
        self.schemes = schemes
        
        # Update the app's router to use our custom route class
        self.app.router.route_class = VersionedAPIRoute
        
        # Add versioning to OpenAPI schema
        self._modify_openapi()
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
            
        request = Request(scope, receive=receive)
        
        # Get version based on configured schemes
        version = None
        for scheme, _ in sorted(self.schemes, key=lambda x: -x[1]):
            if scheme == VersioningScheme.URL:
                version = self._get_version_from_path(request.url.path)
            elif scheme == VersioningScheme.HEADER:
                version = self._get_version_from_header(request)
            elif scheme == VersioningScheme.QUERY:
                version = request.query_params.get(self.version_param)
            elif scheme == VersioningScheme.COOKIE:
                version = request.cookies.get(self.version_cookie)
                
            if version:
                break
                
        # Use default version if none found
        version = version or self.default_version
        
        # Store version in request state
        request.state.api_version = version
        
        # Check if the requested version is supported by the route
        if not self._is_version_supported(scope, version):
            response = Response(
                content={"detail": f"API version {version} not supported for this endpoint"},
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json"
            )
            await response(scope, receive, send)
            return
            
        # Update the path if version was in the URL
        if self._get_version_from_path(request.url.path):
            path_without_version = "/".join([p for p in request.url.path.split("/") if not p.startswith("v")])
            scope["path"] = path_without_version
            
        await self.app(scope, receive, send)
    
    def _get_version_from_path(self, path: str) -> Optional[str]:
        """Extract version from URL path."""
        parts = path.strip("/").split("/")
        if not parts:
            return None
            
        version_match = self.version_regex.match(parts[0])
        if version_match:
            return version_match.group(1)
        return None
    
    def _get_version_from_header(self, request: Request) -> Optional[str]:
        """Extract version from Accept header."""
        accept = request.headers.get(self.version_header, "")
        version_match = re.search(r"version=([\d.]+)", accept)
        if version_match:
            return version_match.group(1)
        return None
    
    def _is_version_supported(self, scope, version: str) -> bool:
        """Check if the requested version is supported by the route."""
        route = scope.get("route")
        if not route:
            return True
            
        endpoint = getattr(route, "endpoint", None)
        if not endpoint:
            return True
            
        min_version = getattr(endpoint, "_min_version", None)
        max_version = getattr(endpoint, "_max_version", None)
        
        if min_version and self._version_compare(version, min_version) < 0:
            return False
            
        if max_version and self._version_compare(version, max_version) > 0:
            return False
            
        return True
    
    @staticmethod
    def _version_compare(v1: str, v2: str) -> int:
        """Compare two version strings."""
        def parse_version(v: str) -> List[int]:
            return [int(part) for part in v.split(".")]
            
        v1_parts = parse_version(v1)
        v2_parts = parse_version(v2)
        
        # Pad with zeros to make lengths equal
        max_length = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_length - len(v1_parts)))
        v2_parts.extend([0] * (max_length - len(v2_parts)))
        
        for v1_part, v2_part in zip(v1_parts, v2_parts):
            if v1_part < v2_part:
                return -1
            elif v1_part > v2_part:
                return 1
                
        return 0
    
    def _modify_openapi(self) -> None:
        """Modify OpenAPI schema to include versioning information."""
        if not self.app.openapi_schema:
            self.app.openapi_schema = {}
            
        original_schema = self.app.openapi
        
        def custom_openapi():
            if self.app.openapi_schema:
                return self.app.openapi_schema
                
            schema = original_schema()
            
            # Add versioning info to the schema
            if "info" not in schema:
                schema["info"] = {}
                
            schema["info"]["version"] = self.default_version
            schema["info"]["x-versions"] = {
                "default": self.default_version,
                "schemes": [{"type": scheme.value, "priority": priority} 
                           for scheme, priority in self.schemes]
            }
            
            # Add version parameter to all paths
            for path in schema.get("paths", {}).values():
                for method in path.values():
                    if not isinstance(method, dict):
                        continue
                        
                    # Add version parameter if not already present
                    parameters = method.get("parameters", [])
                    has_version_param = any(
                        p.get("name") == self.version_param 
                        and p.get("in") == "query"
                        for p in parameters
                    )
                    
                    if not has_version_param:
                        parameters.append({
                            "name": self.version_param,
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "default": self.default_version,
                                "description": "API version"
                            },
                            "description": ("API version. Can also be specified in URL path, "
                                          "Accept header, or cookie.")
                        })
                        method["parameters"] = parameters
            
            self.app.openapi_schema = schema
            return schema
            
        self.app.openapi = custom_openapi
