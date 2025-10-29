"""
Security middleware for the CPIA API.
Includes rate limiting, request size limits, and security headers.
"""
import time
from collections import defaultdict, deque
from typing import Dict, Optional
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    Implements sliding window rate limiting per IP address.
    """
    
    def __init__(self, app, max_requests: int = 100, time_window: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            app: FastAPI application
            max_requests: Maximum requests per time window
            time_window: Time window in seconds (default: 1 hour)
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests outside the time window
        self._cleanup_old_requests(client_ip, current_time)
        
        # Check if client has exceeded rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.max_requests} requests per {self.time_window} seconds allowed",
                    "retry_after": self._calculate_retry_after(client_ip, current_time)
                }
            )
        
        # Add current request timestamp
        self.requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limiting headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.max_requests - len(self.requests[client_ip]))
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + self.time_window)
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded IP (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP (behind load balancer)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_requests(self, client_ip: str, current_time: float):
        """Remove requests outside the time window"""
        cutoff_time = current_time - self.time_window
        client_requests = self.requests[client_ip]
        
        while client_requests and client_requests[0] < cutoff_time:
            client_requests.popleft()
    
    def _calculate_retry_after(self, client_ip: str, current_time: float) -> int:
        """Calculate seconds until client can retry"""
        if not self.requests[client_ip]:
            return 0
        
        oldest_request = self.requests[client_ip][0]
        return max(0, int(oldest_request + self.time_window - current_time))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks"""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            logger.warning(f"Request too large: {content_length} bytes from {request.client}")
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "Request too large",
                    "message": f"Request body must be smaller than {self.max_size} bytes",
                    "max_size": self.max_size
                }
            )
        
        return await call_next(request)


def setup_security_middleware(app, rate_limit_requests: int = 100, rate_limit_window: int = 3600):
    """
    Setup all security middleware for the FastAPI app.
    
    Args:
        app: FastAPI application
        rate_limit_requests: Max requests per time window
        rate_limit_window: Time window in seconds
    """
    # Add middleware in reverse order (last added = first executed)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)
    # Rate limiting temporarily disabled for development/testing
    # app.add_middleware(
    #     RateLimitMiddleware, 
    #     max_requests=rate_limit_requests, 
    #     time_window=rate_limit_window
    # )
    
    logger.info(f"Security middleware configured: Rate limiting DISABLED for development")