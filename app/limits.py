from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Shared limiter instance for the application
limiter = Limiter(key_func=get_remote_address)

# Re-export types for convenience
__all__ = [
    "limiter",
    "RateLimitExceeded",
    "SlowAPIMiddleware",
]
