"""Database bootstrap.

`init_db` creates tables directly and is used for local development, tests and
the demo seed. Production migrations go through Alembic (`alembic upgrade head`)
so schema changes are reviewable and reversible.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Base  # noqa: F401  (imported for metadata registration)
from app.db.session import engine

logger = get_logger(__name__)


def init_db() -> None:
    if settings.environment == "prod":
        # Creating tables implicitly in production would mask a failed migration.
        logger.info("skipping create_all in production; run alembic upgrade head")
        return
    Base.metadata.create_all(bind=engine)
    logger.info("database schema ensured", extra={"url": _safe_url()})


def _safe_url() -> str:
    url = settings.database_url
    if "@" in url:
        scheme, _, rest = url.partition("://")
        _, _, host = rest.partition("@")
        return f"{scheme}://***@{host}"
    return url
