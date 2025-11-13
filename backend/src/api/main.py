import os
import time
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routers.chat import router as chat_router
from src.api.logging_utils import (
    configure_logging,
    get_request_id,
    build_request_log_extra,
    sanitize_headers_for_log,
)

openapi_tags = [
    {
        "name": "Chat",
        "description": "Endpoints for AI chat generation.",
    }
]

app = FastAPI(
    title="Talk 2 AI Backend",
    description="FastAPI backend providing chat via OpenAI.",
    version="0.2.0",
    openapi_tags=openapi_tags,
)

# Initialize structured logging (env-driven LOG_LEVEL supported)
logger = configure_logging()

# Configure CORS: prefer REACT_APP_FRONTEND_URL; always include localhost dev origins
frontend_origin = os.getenv("REACT_APP_FRONTEND_URL")
allowed_origins: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if frontend_origin and frontend_origin not in allowed_origins:
    allowed_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup logging for diagnostics (no secrets)
@app.on_event("startup")
async def _on_startup() -> None:
    logger.info(
        "Backend starting with CORS configuration",
        extra={
            "allowed_origins": allowed_origins,
            "log_level": os.getenv("REACT_APP_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO",
        },
    )

# Request/Response logging middleware with masking and timing
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    req_id = get_request_id(request.headers.get("x-request-id"))
    method = request.method
    path = request.url.path
    origin = request.headers.get("origin") or request.client.host if request.client else None

    # Log request line with sanitized headers (limited)
    try:
        headers_to_log = {k: v for k, v in sanitize_headers_for_log(request.headers.items()).items()
                          if k.lower() in ("host", "user-agent", "origin", "referer", "authorization", "x-api-key")}
        logger.info(
            "Incoming request",
            extra={
                **build_request_log_extra(method, path, origin, req_id),
                "headers": headers_to_log,
            },
        )
    except Exception:
        # Avoid breaking the request if logging fails
        logger.debug("Failed to log request headers", extra={"request_id": req_id})

    try:
        response = await call_next(request)
    except Exception:
        # Centralized exception logging
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.exception(
            "Unhandled exception during request",
            extra={
                **build_request_log_extra(method, path, origin, req_id),
                "duration_ms": duration_ms,
            },
        )
        # Preserve default FastAPI error shape
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    duration_ms = int((time.perf_counter() - start) * 1000)
    status_code = getattr(response, "status_code", 200)

    # Avoid logging response bodies; only status and timing
    logger.info(
        "Request completed",
        extra={
            **build_request_log_extra(method, path, origin, req_id),
            "status_code": status_code,
            "duration_ms": duration_ms,
        },
    )

    # Propagate request id back to client for traceability
    if "x-request-id" not in response.headers:
        response.headers["x-request-id"] = req_id

    return response

# Routers
app.include_router(chat_router)

# PUBLIC_INTERFACE
@app.get("/", tags=["Chat"], summary="Health Check", description="Basic health check endpoint.")
def health_check():
    """Basic health check endpoint."""
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.get(
    "/api/health",
    tags=["Chat"],
    summary="Service health",
    description="Lightweight health endpoint for connectivity checks."
)
def api_health():
    """Return minimal health info and log minimal request context."""
    logger.info("Healthcheck ping", extra={"path": "/api/health"})
    return {"status": "ok"}
