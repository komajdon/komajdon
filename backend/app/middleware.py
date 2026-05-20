from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("komajdon")

# ── Per-endpoint rate limit rules cache ─────────────
_rules: dict[str, dict] = {}  # key = "METHOD:/path"


async def reload_rate_limit_rules(db: AsyncIOMotorDatabase | None = None):
    """Reload per-endpoint rate limit rules from DB into memory."""
    global _rules
    if db is None:
        from app.database import get_db
        try:
            db_gen = get_db()
            db = await db_gen.__anext__()
        except Exception:
            _rules = {}
            return
    try:
        docs = await db["_rate_limits"].find({"enabled": True}).to_list(1000)
        _rules = {}
        for d in docs:
            key = f"{d.get('method', '*').upper()}:{d['endpoint']}"
            _rules[key] = {
                "max_requests": d.get("max_requests", 60),
                "window_seconds": d.get("window_seconds", 60),
            }
        logger.info("Loaded %d rate limit rules", len(_rules))
    except Exception:
        _rules = {}
        logger.warning("Could not load rate limit rules", exc_info=True)


def match_rule(method: str, path: str) -> dict | None:
    """Find the best matching rule for a method+path pair."""
    candidate = _rules.get(f"{method}:{path}")
    if candidate:
        return candidate
    candidate = _rules.get(f"*:{path}")
    if candidate:
        return candidate
    return None


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/api/"):
            start = time.monotonic()
            response = await call_next(request)
            elapsed = time.monotonic() - start
            user_email = getattr(request.state, "user_email", "anonymous")
            client_ip = request.client.host if request.client else "unknown"
            logger.info(
                "AUDIT: %s %s → %s (%dms) user=%s ip=%s",
                request.method, request.url.path, response.status_code,
                int(elapsed * 1000), user_email, client_ip,
            )
            return response
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Callable,
        max_requests: int = 60,
        window_seconds: int = 60,
        auth_endpoints: tuple[str, ...] = ("/api/auth/login", "/api/auth/register", "/api/auth/signin", "/api/auth/signup"),
        auth_max: int = 10,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.auth_endpoints = auth_endpoints
        self.auth_max = auth_max
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_limit(self, method: str, path: str) -> int:
        rule = match_rule(method, path)
        if rule:
            return rule["max_requests"]
        if path in self.auth_endpoints:
            return self.auth_max
        return self.max_requests

    def _is_rate_limited(self, key: str, max_req: int) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        timestamps = [t for t in self._requests[key] if t > window_start]
        self._requests[key] = timestamps
        if len(timestamps) >= max_req:
            return True
        self._requests[key].append(now)
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        max_req = self._get_limit(request.method, request.url.path)
        key = f"rl:{client_ip}:{request.method}:{request.url.path}"
        if self._is_rate_limited(key, max_req):
            return Response(status_code=429, content="Too many requests. Try again later.")
        return await call_next(request)
