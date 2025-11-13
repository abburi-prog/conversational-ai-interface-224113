import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from typing import Any, Dict, Iterable, Optional

SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "x-api-key", "api-key"}
SENSITIVE_PATTERN = re.compile(r"(sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*)", re.IGNORECASE)

def _mask_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    # Replace with a masked token if looks like a key/token
    if SENSITIVE_PATTERN.search(value):
        return "***"
    # If resembles long alphanumeric strings, truncate
    if len(value) > 24:
        return value[:4] + "..." + value[-4:]
    return value

def _mask_headers(headers: Iterable[tuple[str, str]]) -> Dict[str, str]:
    redacted: Dict[str, str] = {}
    for k, v in headers:
        lk = k.lower()
        if lk in SENSITIVE_HEADERS:
            redacted[k] = "***"
        else:
            redacted[k] = _mask_value(v) or ""
    return redacted

class StructuredJsonFormatter(logging.Formatter):
    """Logs records as JSON lines suitable for ingestion by log aggregators."""
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach structured extra if present
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "origin"):
            val = getattr(record, key, None)
            if val is not None:
                base[key] = val
        # exception info
        if record.exc_info:
            base["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stack": "".join(traceback.format_exception(*record.exc_info)),
            }
        return json.dumps(base, ensure_ascii=False)

def configure_logging() -> logging.Logger:
    """Configure root and uvicorn loggers for structured output and level from env."""
    # PUBLIC_INTERFACE
    logger = logging.getLogger("app")
    # Determine log level from environment (default INFO)
    level_name = os.getenv("REACT_APP_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO"
    level = getattr(logging, level_name.upper(), logging.INFO)

    # Reset handlers for idempotent init (e.g., reload)
    for name in ("app", "uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = False
        lg.setLevel(level)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(StructuredJsonFormatter(service_name="talk-2-ai-backend"))

    # App logger
    logger.addHandler(handler)

    # Uvicorn loggers
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.addHandler(handler)

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.addHandler(handler)

    # FastAPI internal
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.addHandler(handler)

    # Root (fallback)
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    logger.debug("Logging configured", extra={"level": logging.getLevelName(level)})
    return logger

def get_request_id(existing: Optional[str] = None) -> str:
    """Return a request ID, using provided header if exists, else generate."""
    # PUBLIC_INTERFACE
    if existing and existing.strip():
        return existing.strip()[:64]
    return str(uuid.uuid4())

def build_request_log_extra(method: str, path: str, origin: Optional[str], request_id: str) -> Dict[str, Any]:
    """Prepare common structured fields for request logs."""
    # PUBLIC_INTERFACE
    return {
        "method": method,
        "path": path,
        "origin": origin or "",
        "request_id": request_id,
    }

def sanitize_headers_for_log(headers: Iterable[tuple[str, str]]) -> Dict[str, str]:
    """Return sanitized headers dict (Authorization and API keys masked)."""
    # PUBLIC_INTERFACE
    return _mask_headers(headers)
