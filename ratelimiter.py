"""
Rate limiting module for protecting API endpoints against abuse.
Uses slowapi for flexible rate limiting based on IP address and endpoints.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

# Initialize rate limiter with default key_func (remote address/IP)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default limit
    storage_uri="memory://",  # In-memory storage (use redis:// for distributed)
    swallow_errors=True  # Don't break app if rate limiter fails
)

# Common limit strategies
LIMITS = {
    'login': "10/minute",              # Login attempts
    'recognition': "30/minute",        # Face recognition attempts
    'enrollment': "20/minute",         # Face enrollment
    'reports': "60/minute",            # Report generation
    'general': "100/minute",           # General API usage
    'strict': "5/minute",              # Strict limit (training, destructive ops)
}

def get_limiter():
    """Get the rate limiter instance."""
    return limiter

def apply_rate_limit(limit_key='general'):
    """
    Decorator to apply rate limiting to an endpoint.
    
    Args:
        limit_key: Key in LIMITS dict or custom "count/period" string
        
    Usage:
        @app.get("/api/endpoint")
        @apply_rate_limit('recognition')
        async def recognize_face():
            ...
    """
    limit_str = LIMITS.get(limit_key, limit_key)
    return limiter.limit(limit_str)

__all__ = ['limiter', 'get_limiter', 'apply_rate_limit', 'LIMITS']