import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("gateway")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status code, and latency."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s → %d  (%.1fms)  ip=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
            request.client.host if request.client else "unknown",
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter: max requests per IP per window.
    Not suitable for multi-instance deployments — use Redis there.
    """

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._counts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Remove timestamps outside the current window
        self._counts[ip] = [t for t in self._counts[ip] if now - t < self.window]

        if len(self._counts[ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {self.max_requests} requests per {self.window}s",
            )

        self._counts[ip].append(now)
        return await call_next(request)
