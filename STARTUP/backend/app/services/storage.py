"""Document blob storage.

Default is the local filesystem. That is a compliance decision, not a shortcut:
scanned invoices carry TINs and personal names, and the posture documented in
docs/data-residency.md keeps those images on infrastructure inside Uzbekistan
while only OCR *text* may leave for cloud NLP.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings

_SAFE_SUFFIX = re.compile(r"[^A-Za-z0-9.]+")


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_storage_key(company_id: int, sha256: str, filename: str) -> str:
    """Content-addressed key, partitioned by company and month.

    Content addressing means re-uploading the same scan cannot create a second
    copy, and the partitioning keeps directory listings usable at volume.
    """
    suffix = _SAFE_SUFFIX.sub("", Path(filename).suffix)[:10].lower() or ".bin"
    if not suffix.startswith("."):
        suffix = "." + suffix
    now = dt.datetime.now(dt.UTC)
    return f"company-{company_id}/{now:%Y/%m}/{sha256}{suffix}"


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> str: ...

    @abstractmethod
    def load(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalStorage(StorageBackend):
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or settings.storage_local_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        root = self.root.resolve()
        # Reject traversal: a crafted key must never escape the storage root.
        if not path.is_relative_to(root):
            raise ValueError(f"Refusing to access path outside storage root: {key}")
        return path

    def save(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write so a crashed upload never leaves a half-written scan.
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(path)
        return key

    def load(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()


class S3Storage(StorageBackend):
    """S3-compatible backend (AWS S3, MinIO, or a local DC object store)."""

    def __init__(self) -> None:
        try:
            import boto3  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "storage_backend='s3' requires boto3 (pip install -r requirements-optional.txt)"
            ) from exc
        if not settings.s3_bucket:
            raise RuntimeError("storage_backend='s3' requires HUJJAT_S3_BUCKET")
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url or None,
        )

    def save(self, key: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def load(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError  # noqa: PLC0415

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError:
            return False
        return True

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _backend  # noqa: PLW0603 - process-wide backend singleton
    if _backend is None:
        _backend = S3Storage() if settings.storage_backend == "s3" else LocalStorage()
    return _backend


def reset_storage() -> None:
    """Test hook: drop the cached backend so settings changes take effect."""
    global _backend  # noqa: PLW0603 - see get_storage
    _backend = None
