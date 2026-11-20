"""Celery tasks for production-volume document processing.

The inline queue is fine for pilot volume; this is what runs when a customer
drops 200 scans in at once and the API must stay responsive.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import session_scope
from app.services import pipeline

logger = get_logger(__name__)

try:
    from celery import Celery
except ImportError:  # pragma: no cover - celery is an optional dependency
    Celery = None  # type: ignore[assignment]


if Celery is not None:
    celery_app = Celery("hujjatai", broker=settings.redis_url, backend=settings.redis_url)
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Tashkent",
        task_acks_late=True,
        # One document per prefetch: OCR is slow and uneven, so a worker holding
        # a queue of them would starve its siblings.
        worker_prefetch_multiplier=1,
        task_reject_on_worker_lost=True,
    )

    @celery_app.task(
        name="hujjatai.process_document",
        bind=True,
        max_retries=3,
        default_retry_delay=30,
        autoretry_for=(ConnectionError, TimeoutError),
    )
    def process_document_task(self, document_id: int) -> dict:
        configure_logging(settings.log_level)
        with session_scope() as db:
            document = pipeline.process_document(db, document_id)
            return {"document_id": document.id, "status": document.status}
else:  # pragma: no cover
    celery_app = None

    def process_document_task(document_id: int) -> dict:
        raise RuntimeError(
            "queue_backend='celery' requires celery (pip install -r requirements-optional.txt)"
        )
