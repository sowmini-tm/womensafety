"""Production security & reliability middleware.

Provides:
- security response headers
- a lightweight in-process fixed-window rate limiter (no Redis/external service)
- a request-body size cap

All state is in-memory and per-process, which is an appropriate, dependency-free
defense for a small deployment. Limits are configurable so tests can exercise
the 429 path without timing-sensitive sleeps.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .config import settings

# Fixed-window rate limit buckets: { (client_ip, scope): (window_start, count) }.
_rate_buckets: dict[tuple[str, str], tuple[float, int]] = {}

# Scopes applied to sensitive endpoints. Each config value is (max_requests, window_seconds).
RATE_LIMIT_SCOPES = {
    "auth": (settings.RATE_LIMIT_AUTH_MAX or 10, settings.RATE_LIMIT_WINDOW_SECONDS or 60),
    "otp": (settings.RATE_LIMIT_OTP_MAX or 6, settings.RATE_LIMIT_WINDOW_SECONDS or 60),
    "sos": (settings.RATE_LIMIT_SOS_MAX or 5, settings.RATE_LIMIT_WINDOW_SECONDS or 60),
    "shared": (settings.RATE_LIMIT_SHARED_MAX or 60, settings.RATE_LIMIT_WINDOW_SECONDS or 60),
}


def _rate_limit_scope(path: str) -> str | None:
    if path.endswith("/auth/login") or path.endswith("/auth/register"):
        return "auth"
    if (
        "/auth/register/verify" in path
        or "/auth/register/resend-verification" in path
        or "/auth/forgot-password" in path
        or "/auth/reset-password" in path
    ):
        return "otp"
    if path.endswith("/safety/sos"):
        return "sos"
    if "/safety/shared-location/" in path:
        return "shared"
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window in-memory rate limiting keyed by client IP + scope."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.ENABLE_RATE_LIMITING:
            return await call_next(request)
        scope = _rate_limit_scope(request.url.path)
        if scope is None:
            return await call_next(request)

        max_requests, window = RATE_LIMIT_SCOPES[scope]
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, scope)

        now = time.monotonic()
        window_start, count = _rate_buckets.get(key, (now, 0))
        if now - window_start >= window:
            window_start, count = now, 0
        count += 1
        _rate_buckets[key] = (window_start, count)

        if count > max_requests:
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set safe-by-default HTTP security headers without breaking the app."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Cache-Control", "no-store"
        )  # sensitive location/safety API responses
        return response


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies before they are parsed.

    FastAPI/Starlette buffers request bodies in memory; capping the size is a
    cheap sanity guard against abuse. 1 MB is generous for this app's JSON.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(status_code=413, content={"detail": "Request body too large."})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})
        return await call_next(request)
