"""Rate limiting middleware for API endpoints."""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


class RateLimiter:
    """
    Simple in-memory rate limiter.

    For production with multiple servers, use Redis-backed rate limiting.
    This implementation uses a sliding window algorithm.
    """

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute per key
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds

        # Store: {key: [(timestamp1, ), (timestamp2, ), ...]}
        self.requests: Dict[str, list] = defaultdict(list)

    def _clean_old_requests(self, key: str, current_time: float):
        """Remove requests older than the window size."""
        cutoff_time = current_time - self.window_size
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if timestamp > cutoff_time
        ]

    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """
        Check if a request is allowed for the given key.

        Args:
            key: Unique identifier (e.g., tenant_id, IP address, API key)

        Returns:
            Tuple of (allowed: bool, rate_limit_info: dict)
        """
        current_time = time.time()

        # Clean old requests
        self._clean_old_requests(key, current_time)

        # Check if under limit
        request_count = len(self.requests[key])
        allowed = request_count < self.requests_per_minute

        if allowed:
            self.requests[key].append(current_time)

        # Calculate reset time
        if self.requests[key]:
            oldest_request = min(self.requests[key])
            reset_time = int(oldest_request + self.window_size)
        else:
            reset_time = int(current_time + self.window_size)

        rate_limit_info = {
            "limit": self.requests_per_minute,
            "remaining": max(0, self.requests_per_minute - request_count - (1 if allowed else 0)),
            "reset": reset_time,
            "used": request_count + (1 if allowed else 0)
        }

        return allowed, rate_limit_info


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60)


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.

    Rate limits by tenant_id if available, otherwise by IP address.
    """
    # Skip rate limiting for health check and root endpoints
    if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    # Determine rate limit key
    # Priority: tenant_id from path > API key > IP address
    rate_limit_key = None

    # Extract tenant_id from path (e.g., /api/demo/chat)
    path_parts = request.url.path.split("/")
    if len(path_parts) >= 3 and path_parts[1] == "api":
        rate_limit_key = f"tenant_{path_parts[2]}"

    # Fallback to API key if present
    if not rate_limit_key:
        api_key = request.headers.get("x-api-key")
        if api_key:
            rate_limit_key = f"api_key_{api_key[:16]}"  # Use first 16 chars

    # Fallback to IP address
    if not rate_limit_key:
        client_ip = request.client.host if request.client else "unknown"
        rate_limit_key = f"ip_{client_ip}"

    # Check rate limit
    allowed, rate_info = rate_limiter.is_allowed(rate_limit_key)

    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "rate_limit": rate_info
            },
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": str(rate_info["remaining"]),
                "X-RateLimit-Reset": str(rate_info["reset"]),
                "Retry-After": str(rate_info["reset"] - int(time.time()))
            }
        )

    # Add rate limit headers to response
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

    return response


# ============================================================================
# Redis-based Rate Limiter (for production with multiple servers)
# ============================================================================

class RedisRateLimiter:
    """
    Redis-backed rate limiter for distributed systems.

    Usage:
        from redis import Redis
        redis_client = Redis(host='localhost', port=6379, db=0)
        rate_limiter = RedisRateLimiter(redis_client, requests_per_minute=60)
    """

    def __init__(self, redis_client, requests_per_minute: int = 60):
        """
        Initialize Redis rate limiter.

        Args:
            redis_client: Redis client instance
            requests_per_minute: Maximum requests per minute
        """
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute
        self.window_size = 60

    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """Check if request is allowed using Redis sorted set."""
        current_time = time.time()
        redis_key = f"rate_limit:{key}"

        # Remove old entries
        self.redis.zremrangebyscore(
            redis_key,
            0,
            current_time - self.window_size
        )

        # Count requests in window
        request_count = self.redis.zcard(redis_key)
        allowed = request_count < self.requests_per_minute

        if allowed:
            # Add current request
            self.redis.zadd(redis_key, {str(current_time): current_time})
            # Set expiry
            self.redis.expire(redis_key, self.window_size)

        # Get reset time
        oldest_scores = self.redis.zrange(redis_key, 0, 0, withscores=True)
        if oldest_scores:
            oldest_time = oldest_scores[0][1]
            reset_time = int(oldest_time + self.window_size)
        else:
            reset_time = int(current_time + self.window_size)

        rate_limit_info = {
            "limit": self.requests_per_minute,
            "remaining": max(0, self.requests_per_minute - request_count - (1 if allowed else 0)),
            "reset": reset_time,
            "used": request_count + (1 if allowed else 0)
        }

        return allowed, rate_limit_info


# ============================================================================
# Dependency for route-specific rate limiting
# ============================================================================

def get_rate_limiter():
    """Dependency to get rate limiter instance."""
    return rate_limiter


async def check_rate_limit(request: Request, limiter: RateLimiter = None):
    """
    Dependency for explicit rate limiting in specific routes.

    Usage:
        @app.post("/api/expensive-operation")
        async def expensive_op(
            rate_limit: None = Depends(check_rate_limit)
        ):
            # Your code here
    """
    if limiter is None:
        limiter = rate_limiter

    # Extract key (similar logic as middleware)
    path_parts = request.url.path.split("/")
    if len(path_parts) >= 3 and path_parts[1] == "api":
        key = f"tenant_{path_parts[2]}"
    else:
        api_key = request.headers.get("x-api-key", "")
        key = f"api_key_{api_key[:16]}" if api_key else f"ip_{request.client.host}"

    allowed, rate_info = limiter.is_allowed(key)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": str(rate_info["remaining"]),
                "X-RateLimit-Reset": str(rate_info["reset"]),
                "Retry-After": str(rate_info["reset"] - int(time.time()))
            }
        )