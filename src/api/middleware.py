from __future__ import annotations

import time
import uuid
from typing import Callable, Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.common.settings import SETTINGS


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)

        response.headers["x-request-id"] = request_id
        response.headers["x-latency-ms"] = str(latency_ms)
        return response


class RateLimiter:
    """
    Simple in-memory per-IP rate limiter (requests per minute).
    Demo-only (not distributed).
    """
    def __init__(self, rpm: int):
        self.rpm = max(1, int(rpm))
        self.window_sec = 60
        self.hits: Dict[str, list[float]] = {}

    def allow(self, key: str, now: float) -> bool:
        arr = self.hits.get(key)
        if arr is None:
            self.hits[key] = [now]
            return True

        cutoff = now - self.window_sec
        i = 0
        while i < len(arr) and arr[i] < cutoff:
            i += 1
        if i > 0:
            del arr[:i]

        if len(arr) >= self.rpm:
            return False
        arr.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rpm: int):
        super().__init__(app)
        self.limiter = RateLimiter(rpm=rpm)

    async def dispatch(self, request: Request, call_next: Callable):
        now = time.time()
        ip = request.client.host if request.client else "unknown"
        if not self.limiter.allow(ip, now):
            return Response(
                content="rate_limited",
                status_code=429,
                media_type="text/plain",
                headers={"retry-after": "10"},
            )
        return await call_next(request)