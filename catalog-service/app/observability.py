"""One JSON log line per request.

Fields: method, path, query, operation, status, latency, result count, error code
and the API key's fingerprint (first 6 hex characters of its SHA-256). The key
itself and request headers are never logged.
"""

from __future__ import annotations

import json
import logging
import time

from fastapi import FastAPI, Request

access_logger = logging.getLogger("catalog.access")


def install_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def _log_request(request: Request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # The 500 handler renders the envelope outside this middleware: log the line here.
            request.state.error_code = "internal_error"
            _write_line(request, 500, started)
            raise
        _write_line(request, response.status_code, started)
        return response


def _write_line(request: Request, status: int, started: float) -> None:
    route = request.scope.get("route")
    operation = getattr(route, "operation_id", None) or getattr(route, "name", None)
    state = request.state
    access_logger.info(
        json.dumps(
            {
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query or None,
                "operation": operation,
                "status": status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "result_count": getattr(state, "result_count", None),
                "error_code": getattr(state, "error_code", None),
                "key_fingerprint": getattr(state, "key_fingerprint", None),
            },
            separators=(",", ":"),
        )
    )
