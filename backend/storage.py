"""Supabase Storage helpers for uploaded question-paper PDFs."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from supabase import Client, create_client

BUCKET_NAME = os.environ.get("SUPABASE_BUCKET", "pyq-pdfs")
logger = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """Raised when Supabase Storage is unavailable or misconfigured."""


def _log_provider_error(operation: str, exc: Exception) -> None:
    """Log actionable provider details without exposing configured secrets."""
    detail = str(exc)
    for secret_name in ("SUPABASE_SERVICE_ROLE_KEY", "MYSQL_PASSWORD", "FLASK_SECRET_KEY"):
        secret = os.environ.get(secret_name)
        if secret:
            detail = detail.replace(secret, "<redacted>")
    logger.error(
        "Supabase Storage %s failed (%s): %s",
        operation,
        type(exc).__name__,
        detail[:1000],
    )


@lru_cache(maxsize=1)
def _client() -> Client:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise StorageError("Supabase storage credentials are not configured.")
    try:
        return create_client(url, key)
    except Exception as exc:
        _log_provider_error("client initialization", exc)
        raise StorageError("Could not initialize Supabase Storage client.") from exc


def upload_pdf(object_key: str, content: bytes) -> None:
    if not object_key.startswith("papers/") or ".." in object_key.split("/"):
        raise StorageError("Invalid PDF storage key.")
    try:
        _client().storage.from_(BUCKET_NAME).upload(
            object_key,
            content,
            file_options={"content-type": "application/pdf", "upsert": "false"},
        )
    except Exception as exc:
        _log_provider_error("upload", exc)
        raise StorageError("Could not upload PDF to Supabase Storage.") from exc


def download_pdf(object_key: str) -> bytes:
    if not object_key.startswith("papers/") or ".." in object_key.split("/"):
        raise StorageError("Invalid PDF storage key.")
    try:
        result = _client().storage.from_(BUCKET_NAME).download(object_key)
        if not isinstance(result, bytes) or not result.startswith(b"%PDF-"):
            raise StorageError("Stored object is not a valid PDF.")
        return result
    except StorageError:
        raise
    except Exception as exc:
        _log_provider_error("download", exc)
        raise StorageError("Could not download PDF from Supabase Storage.") from exc


def delete_pdf(object_key: str) -> None:
    if not object_key.startswith("papers/") or ".." in object_key.split("/"):
        raise StorageError("Invalid PDF storage key.")
    try:
        _client().storage.from_(BUCKET_NAME).remove([object_key])
    except Exception as exc:
        _log_provider_error("delete", exc)
        raise StorageError("Could not delete PDF from Supabase Storage.") from exc
