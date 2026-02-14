"""
Ekodi – Load protection middleware.

Wraps the entire ASGI app and:
  1. Tracks active requests in the server monitor
  2. Rejects requests with 503 when the server is overloaded
  3. Adds server status headers to responses
  4. Measures response time

Heavy endpoints (/chat, /voice-chat, /tts) are protected.
Static files and health checks always pass through.
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.server_monitor import get_monitor

logger = logging.getLogger(__name__)

# Paths that are always allowed (never rejected)
PASSTHROUGH_PREFIXES = (
    "/health",
    "/status",
    "/assets/",
    "/favicon",
    "/logo-",
    "/auth/login",
    "/auth/register",
    "/auth/me",
    "/auth/refresh",
    "/admin/",
)

# Heavy endpoints that consume GPU/CPU resources — protected
HEAVY_ENDPOINTS = (
    "/chat",
    "/voice-chat",
    "/tts",
)


class LoadProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware that rejects requests when server is overloaded."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Always allow passthrough paths and OPTIONS
        if method == "OPTIONS" or any(path.startswith(p) for p in PASSTHROUGH_PREFIXES):
            return await call_next(request)

        monitor = get_monitor()

        # Check overload only for heavy endpoints
        is_heavy = any(path.endswith(ep) or path.startswith(ep) for ep in HEAVY_ENDPOINTS)

        if is_heavy:
            is_overloaded, reason = monitor.check_overloaded()
            if is_overloaded:
                monitor.record_rejection()
                logger.warning("Request rejected (503): %s %s — %s", method, path, reason)
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "Server is currently busy. Please try again in a moment.",
                        "error": "server_busy",
                        "reason": reason,
                        "retry_after": 10,
                    },
                    headers={
                        "Retry-After": "10",
                        "X-Server-Status": "busy",
                    },
                )

        # Track request
        monitor.request_start()
        start = time.time()
        error = False

        try:
            response = await call_next(request)

            if response.status_code >= 500:
                error = True

            # Add server status header
            status_level = monitor.get_status_level()
            response.headers["X-Server-Status"] = status_level

            return response

        except Exception as exc:
            error = True
            raise exc

        finally:
            duration_ms = (time.time() - start) * 1000
            monitor.request_end(duration_ms, error=error)
