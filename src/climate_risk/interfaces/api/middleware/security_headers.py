"""Security headers middleware for FastAPI."""
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ....config.settings import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses.
    
    This middleware adds various security-related HTTP headers to help protect
    against common web vulnerabilities.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> None:
        """Initialize the middleware.
        
        Args:
            app: The ASGI application.
            headers: Custom security headers to add or override.
            **kwargs: Additional arguments to pass to the base class.
        """
        super().__init__(app, **kwargs)
        self.headers = headers or {}
        
        # Default security headers
        self.default_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Enable XSS filtering in browsers that support it
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                                      "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
                                      "connect-src 'self';",
            
            # Feature Policy (now Permissions Policy in newer browsers)
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
            
            # HTTP Strict Transport Security (HSTS)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # X-Permitted-Cross-Domain-Policies
            "X-Permitted-Cross-Domain-Policies": "none",
            
            # X-Download-Options for IE8+
            "X-Download-Options": "noopen",
            
            # Prevent browsers from detecting the MIME type as something other than declared
            "X-Content-Type-Options": "nosniff",
            
            # Disable caching by default (can be overridden per-route)
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Surrogate-Control": "no-store",
        }
        
        # Update with any headers from settings
        if hasattr(settings, 'SECURE_HEADERS') and isinstance(settings.SECURE_HEADERS, dict):
            self.default_headers.update(settings.SECURE_HEADERS)
        
        # Update with any custom headers provided during initialization
        if self.headers:
            self.default_headers.update(self.headers)
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and add security headers to the response.
        
        Args:
            request: The incoming request.
            call_next: The next middleware or route handler.
            
        Returns:
            Response: The response with security headers added.
        """
        response = await call_next(request)
        
        # Don't add headers to websocket requests
        if request.url.path.startswith("/ws"):
            return response
            
        # Add security headers
        for header, value in self.default_headers.items():
            # Don't override existing headers unless they're empty
            if header not in response.headers or not response.headers[header]:
                response.headers[header] = value
                
        # Add security headers that should always be set
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Add HSTS header for HTTPS requests
        if request.url.scheme == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
            
        return response


def add_security_headers(app: ASGIApp, **kwargs: Any) -> None:
    """Add security headers middleware to the application.
    
    This is a convenience function to add the security headers middleware
    with the specified configuration.
    
    Args:
        app: The FastAPI application.
        **kwargs: Additional arguments to pass to SecurityHeadersMiddleware.
    """
    app.add_middleware(SecurityHeadersMiddleware, **kwargs)
