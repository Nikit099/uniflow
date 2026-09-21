import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, ai, auth, cases, health, max_webhook, sources, staff
from app.core.config import get_settings
from app.core.rate_limit import SlidingWindowLimiter

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("uniflow")
limiter = SlidingWindowLimiter()

app = FastAPI(
    title="UniFlow API",
    version="0.1.0",
    description="Case management for international student administrative procedures. University verification is not a government decision.",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    client_ip = request.client.host if request.client else "unknown"
    sensitive_limits = {
        "/api/v1/auth/demo/login": 30,
        "/api/v1/auth/max": 30,
        "/api/v1/integrations/max/webhook": 120,
    }
    limit = (
        30 if request.url.path.startswith("/api/v1/ai/") else sensitive_limits.get(request.url.path)
    )
    if limit and not limiter.allow(f"{client_ip}:{request.url.path}", limit):
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests",
                    "request_id": request_id,
                }
            },
            headers={"Retry-After": "60", "X-Request-ID": request_id},
        )
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed", extra={"request_id": request_id, "path": request.url.path}
        )
        raise
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
    )
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": round((time.perf_counter() - started) * 1000),
        },
    )
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("x-request-id", "unknown")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error",
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = request.headers.get("x-request-id", "unknown")
    code = str(exc.detail).upper().replace(" ", "_")[:80]
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail), "request_id": request_id}},
        headers=exc.headers,
    )


for router in (
    auth.router,
    cases.router,
    staff.router,
    admin.router,
    ai.router,
    sources.router,
    max_webhook.router,
):
    app.include_router(router, prefix="/api/v1")
app.include_router(health.router)
