from __future__ import annotations

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("komajdon")


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
