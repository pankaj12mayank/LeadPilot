"""Global HTTP and validation error responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import config

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail: Any = exc.detail
        if isinstance(detail, str):
            body = {"detail": detail}
        else:
            body = {"detail": detail}
        if exc.status_code >= 500:
            logger.error("%s %s -> HTTP %s: %s", request.method, request.url.path, exc.status_code, detail)
        elif exc.status_code >= 400:
            logger.warning("%s %s -> HTTP %s: %s", request.method, request.url.path, exc.status_code, detail)
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "message": "Validation error"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        body: dict = {"detail": "Internal server error"}
        if getattr(config, "DEBUG", False) or bool(getattr(request.app, "debug", False)):
            body["message"] = str(exc)
        return JSONResponse(status_code=500, content=body)
