"""Liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings
from app.services.extract.llm import LLMExtractor
from app.services.ocr.registry import build_chain

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@router.get("/ready")
def ready(db: DbSession) -> dict:
    """Readiness: reports which processing capabilities are actually wired up.

    Deployments routinely come up with a missing API key, and the failure would
    otherwise only surface as unexplained low accuracy days later.
    """
    checks: dict[str, object] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    checks["ocr_providers"] = {
        provider.name: provider.is_available() for provider in build_chain()
    }
    checks["llm_configured"] = LLMExtractor().is_available()
    checks["extraction_strategy"] = settings.extraction_strategy
    checks["storage_backend"] = settings.storage_backend
    checks["queue_backend"] = settings.queue_backend

    ocr_ready = any(checks["ocr_providers"].values())
    status = "ok" if checks["database"] is True and ocr_ready else "degraded"
    return {"status": status, "checks": checks}
