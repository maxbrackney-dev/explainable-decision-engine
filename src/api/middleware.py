from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.common.logging import get_logger

logger = get_logger("middleware")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)

        response.headers["x-request-id"] = request_id
        response.headers["x-latency-ms"] = str(latency_ms)

        # consistent JSON log
        logger.info(
            "http_request",
            extra={
                "ctx": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": latency_ms,
                }
            },
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # Auth/rate limiting is enforced in routes for /v1/*
        return await call_next(request)
