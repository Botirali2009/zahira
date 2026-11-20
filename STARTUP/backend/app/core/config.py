"""Application configuration.

All settings are environment-driven so the same image runs in dev, staging and
production. Defaults are chosen so that `uvicorn app.main:app` works on a clean
checkout with no external services: SQLite database, local file storage,
in-process task queue and the rule-based extractor.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="HUJJAT_",
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    app_name: str = "HujjatAI"
    environment: Literal["dev", "test", "staging", "prod"] = "dev"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # Comma-separated list of allowed browser origins for the SPA.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Security ----------------------------------------------------------
    # Generated per-process when unset, which is fine for dev and fatal-by-check
    # in prod (see `validate_production_settings`).
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    access_token_ttl_minutes: int = 60 * 12
    refresh_token_ttl_days: int = 30
    password_min_length: int = 10

    # --- Database ----------------------------------------------------------
    database_url: str = f"sqlite:///{BASE_DIR / 'hujjat.db'}"

    # --- Storage -----------------------------------------------------------
    # "local" keeps document images inside Uzbekistan, which is the compliance
    # posture described in docs/data-residency.md. "s3" is available for
    # non-personal-data deployments and for the future local S3-compatible DC.
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: Path = BASE_DIR / "var" / "documents"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "eu-central-1"

    max_upload_mb: int = 10
    max_batch_files: int = 20
    allowed_mime_types: str = "application/pdf,image/jpeg,image/png,image/tiff"

    # --- OCR ---------------------------------------------------------------
    # Ordered fallback chain. The first provider that reports itself available
    # and returns text wins. "pdf_text" handles born-digital e-invoices for free.
    ocr_providers: str = "pdf_text,google_vision,tesseract"
    google_vision_api_key: str = ""
    google_vision_endpoint: str = "https://vision.googleapis.com/v1/images:annotate"
    tesseract_cmd: str = "tesseract"
    tesseract_languages: str = "uzb+uzb_cyrl+rus"
    ocr_timeout_seconds: float = 30.0

    # --- Extraction --------------------------------------------------------
    # "rules" is deterministic, free and offline. "llm" calls an
    # OpenAI-compatible chat completions endpoint. "auto" runs rules first and
    # escalates to the LLM only when rule confidence is below the threshold,
    # which is what keeps per-document cost near zero.
    extraction_strategy: Literal["rules", "llm", "auto"] = "auto"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 45.0
    llm_escalation_threshold: float = 0.80

    # Number of accepted corrections from one vendor before the learned
    # template takes priority over generic label search.
    template_learning_threshold: int = 5

    # --- Processing --------------------------------------------------------
    # "inline" processes in a FastAPI background task (fine to ~5 docs/min/worker),
    # "celery" hands off to a Redis-backed worker for production volume.
    queue_backend: Literal["inline", "celery"] = "inline"
    redis_url: str = "redis://localhost:6379/0"
    processing_concurrency: int = 4

    # --- Business ----------------------------------------------------------
    vat_rate_percent: float = 12.0  # Uzbekistan standard VAT since 2023
    default_currency: str = "UZS"

    @field_validator("storage_local_root", mode="before")
    @classmethod
    def _expand_path(cls, value: object) -> object:
        if isinstance(value, str):
            return Path(value).expanduser()
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ocr_provider_list(self) -> list[str]:
        return [name.strip() for name in self.ocr_providers.split(",") if name.strip()]

    @property
    def allowed_mime_list(self) -> list[str]:
        return [mime.strip() for mime in self.allowed_mime_types.split(",") if mime.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def validate_production_settings(self) -> list[str]:
        """Return a list of misconfigurations that must not ship to production."""
        problems: list[str] = []
        if self.environment != "prod":
            return problems
        if "HUJJAT_SECRET_KEY" not in _env_keys():
            problems.append(
                "HUJJAT_SECRET_KEY is unset: tokens would be invalidated on every restart"
            )
        if self.database_url.startswith("sqlite"):
            problems.append("SQLite is not supported in production; set HUJJAT_DATABASE_URL")
        if self.debug:
            problems.append("HUJJAT_DEBUG must be false in production")
        return problems


def _env_keys() -> set[str]:
    import os  # noqa: PLC0415 - local import keeps this helper self-contained

    return set(os.environ)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
