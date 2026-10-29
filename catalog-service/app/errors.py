"""The error envelope.

Recoverable cases (something the agent asked for does not exist) answer 200 with
`found: false`, so the model reads the hints whatever the platform does with 4xx.
Failures keep their HTTP status. Both carry the same `error` object.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("catalog")


class ErrorBody(BaseModel):
    code: str = Field(description="Stable machine-readable error code, e.g. `category_not_found`.")
    message: str = Field(description="What went wrong, in one sentence.")
    hint: str = Field(description="The next action to take to recover.")
    did_you_mean: list[str] | None = Field(
        default=None, description="Closest valid values to what was sent, best first."
    )
    valid_values: list[str] | None = Field(
        default=None, description="Every valid value for the parameter that failed."
    )


class ErrorResponse(BaseModel):
    found: bool | None = Field(
        default=None,
        description="`false` on recoverable not-found cases (HTTP 200). Absent on failures.",
    )
    error: ErrorBody = Field(description="What went wrong and how to recover.")


class CatalogError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        hint: str,
        status_code: int = 200,
        *,
        did_you_mean: list[str] | None = None,
        valid_values: list[str] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers
        self.body = ErrorBody(
            code=code,
            message=message,
            hint=hint,
            did_you_mean=did_you_mean,
            valid_values=valid_values,
        )

    @property
    def recoverable(self) -> bool:
        return self.status_code == 200

    def response(self) -> JSONResponse:
        payload = ErrorResponse(found=False if self.recoverable else None, error=self.body)
        return JSONResponse(
            payload.model_dump(exclude_none=True),
            status_code=self.status_code,
            headers=self.headers,
        )


def unauthorized() -> CatalogError:
    return CatalogError(
        "unauthorized",
        "Missing or invalid API key.",
        "Send a valid key in the X-API-Key header.",
        status_code=401,
    )


def _describe(error: dict) -> str:
    location = ".".join(str(part) for part in error["loc"] if part not in ("query", "path", "body"))
    return f"{location}: {error['msg']}" if location else error["msg"]


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(CatalogError)
    async def _catalog_error(_: Request, exc: CatalogError) -> JSONResponse:
        return exc.response()

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        message = "; ".join(_describe(error) for error in exc.errors())
        return CatalogError(
            "invalid_parameter",
            f"Invalid parameters: {message}.",
            "Fix the listed parameters and call again.",
            status_code=422,
        ).response()

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", exc_info=exc)
        return CatalogError(
            "internal_error",
            "The catalogue service had an unexpected problem.",
            "Try again once; if it fails again, tell the shopper the catalogue is unavailable.",
            status_code=500,
        ).response()
