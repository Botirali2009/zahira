"""HujjatAI API application."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, dashboard, documents, exports, health
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, request_id_var
from app.db.base import init_db

logger = get_logger(__name__)

DESCRIPTION = """\
Document AI for Uzbek business accounting.

Extracts structured data from `hisob-faktura` / `счёт-фактура` invoices written
in any mix of Uzbek Latin, Uzbek Cyrillic and Russian, and exports it as
CommerceML 2.08 for import into 1C:Buxgalteriya 8.3.

Every extracted field carries a confidence score and the evidence it came from.
Nothing reaches 1C without a human confirming it.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)

    problems = settings.validate_production_settings()
    if problems:
        # Refuse to serve production traffic with a configuration that would
        # lose sessions on restart or run on a single-file database.
        for problem in problems:
            logger.error("invalid production configuration", extra={"problem": problem})
        raise RuntimeError("Invalid production configuration: " + "; ".join(problems))

    init_db()
    logger.info(
        "application started",
        extra={"environment": settings.environment, "storage": settings.storage_backend,
               "queue": settings.queue_backend, "strategy": settings.extraction_strategy},
    )
    yield
    logger.info("application stopped")


app = FastAPI(
    title=settings.app_name,
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Tag every request with an id and log its latency."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    duration_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    if request.url.path not in ("/health", "/ready"):
        logger.info(
            "request",
            extra={"method": request.method, "path": request.url.path,
                   "status": response.status_code, "duration_ms": duration_ms,
                   "request_id": request_id},
        )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return field errors in a shape the UI can attach to specific inputs."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation failed",
            "errors": [
                {"field": ".".join(str(part) for part in error.get("loc", [])[1:]),
                 "message": error.get("msg", "")}
                for error in exc.errors()
            ],
        },
    )


app.include_router(health.router)
for router in (auth.router, documents.router, exports.router, dashboard.router):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": app.version,
        "docs": "/docs",
        "api": settings.api_prefix,
    }
