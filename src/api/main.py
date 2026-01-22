from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.common.settings import SETTINGS
from src.common.otel import setup_otel
from src.api.middleware import RequestTracingMiddleware, RateLimitMiddleware
from src.api.routes import router

app = FastAPI(title=SETTINGS.project_name, version=SETTINGS.api_version)

# Observability
setup_otel(app, service_name=SETTINGS.project_name)

# Middleware
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RateLimitMiddleware)

# API routes (auth enforced inside /v1 routes via dependency)
app.include_router(router, prefix=f"/{SETTINGS.api_version}")

# Serve the V3 UI static assets
app.mount("/static", StaticFiles(directory="src/api/site/static"), name="static")


# ---- UI Pages (customer-friendly portal) ----
@app.get("/", include_in_schema=False)
def landing():
    return FileResponse("src/api/site/index.html")


@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse("src/api/site/login.html")


@app.get("/app", include_in_schema=False)
def app_page():
    return FileResponse("src/api/site/app.html")


@app.get("/audit", include_in_schema=False)
def audit_page():
    return FileResponse("src/api/site/audit.html")


@app.get("/metrics", include_in_schema=False)
def metrics_page():
    return FileResponse("src/api/site/metrics.html")


@app.get("/report", include_in_schema=False)
def report_page():
    return FileResponse("src/api/site/report.html")
