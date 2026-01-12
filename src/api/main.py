from __future__ import annotations

from fastapi import FastAPI

from src.common.settings import SETTINGS
from src.api.routes import router
from src.api.middleware import RequestTracingMiddleware, RateLimitMiddleware

app = FastAPI(title=SETTINGS.project_name, version=SETTINGS.api_version)

app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RateLimitMiddleware, rpm=SETTINGS.rate_limit_rpm)

app.include_router(router, prefix=f"/{SETTINGS.api_version}")