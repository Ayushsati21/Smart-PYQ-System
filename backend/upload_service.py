"""Safe single-PDF ingestion for the Smart PYQ Flask API.

The OCR and question parsing implementations remain in their existing modules.
This service only coordinates upload storage, processing, and one transaction.
"""

from __future__ import annotations

import os
import re
import logging
import uuid
from pathlib import Path
from typing import Any

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .db import DatabaseConfigurationError, DatabaseQueryError, get_connection
from .storage import StorageError, delete_pdf, upload_pdf


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = BASE_DIR / "input_pdfs"
OUTPUT_DIR = BASE_DIR / "output_text"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
REQUIRED_FIELDS = ("course", "subject", "academic_year", "semester", "exam_year", "term", "paper_code")
logger = logging.getLogger(__name__)


def _safe_error_detail(error: Exception) -> str:
    detail = str(error)
    password = os.environ.get("MYSQL_PASSWORD")
    if password:
        detail = detail.replace(password, "<redacted>")
    return detail[:500]


class UploadValidationError(ValueError):
    """Raised when the multipart upload is invalid."""


class UploadProcessingError(RuntimeError):
    """Raised when OCR or database persistence fails."""


def _required_metadata(form: Any) -> dict[str, str | int]:
    values = {field: str(form.get(field, "")).strip() for field in REQUIRED_FIELDS}
    missing = [field for field, value in values.items() if not value]
    if missing:
        raise UploadValidationError("Missing required metadata: " + ", ".join(missing))

    try:
        exam_year = int(values["exam_year"])
    except ValueError as exc:
        raise UploadValidationError("exam_year must be an integer.") from exc

    if not 1900 <= exam_year <= 2200:
        raise UploadValidationError("exam_year must be between 1900 and 2200.")

    values["exam_year"] = exam_year
    return values


def _safe_pdf_name(original_name: str) -> str:
    safe_name = secure_filename(original_name or "")
    if not safe_name or Path(safe_name).suffix.casefold() != ".pdf":
        raise UploadValidationError("Only PDF files with a .pdf extension are accepted.")
    if Path(safe_name).name != safe_name:
        raise UploadValidationError("The PDF filename is not safe.")
    return safe_name


def _write_upload(file: FileStorage, destination: Path) -> None:
    written = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        while True:
            chunk = file.stream.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                raise UploadValidationError("PDF exceeds the 25 MB upload limit.")
            output.write(chunk)

    if written < 5 or destination.read_bytes()[:5] != b"%PDF-":
        raise UploadValidationError("The uploaded file does not have a valid PDF signature.")


def _unique_name(safe_name: str) -> str:
    candidate = INPUT_DIR / safe_name
    text_candidate = OUTPUT_DIR / f"{Path(safe_name).stem}.txt"
    if not candidate.exists() and not text_candidate.exists():
        return safe_name
    stem = Path(safe_name).stem
    return f"{stem}-{uuid.uuid4().hex[:10]}.pdf"


def _character_count(text: str) -> int:
    pages = re.split(r"(?m)^--- PAGE \d+ ---\s*\r?\n", text)
    return sum(len(page.strip()) for page in pages[1:]) if len(pages) > 1 else len(text.strip())


def _persist(
    metadata: dict[str, str | int],
    pdf_name: str,
    pdf_relative_path: str,
    text_relative_path: str,
    extracted_text: str,
    total_pages: int,
    questions: list[dict[str, Any]],
) -> tuple[int, list[str]]:
    """Persist the paper and questions using the existing transaction shape."""

    connection = get_connection()
    cursor = None
    warnings: list[str] = []
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW COLUMNS FROM question_papers")
        columns = {row[0] for row in cursor.fetchall()}
        required = {
            "id", "pdf_filename", "pdf_relative_path", "text_file_path", "course", "subject",
            "academic_year", "semester", "paper_code", "exam_year", "term",
            "total_pages", "ocr_characters", "extracted_text",
        }
        missing = required - columns
        if missing:
            raise UploadProcessingError(
                "question_papers is missing required columns: " + ", ".join(sorted(missing))
            )

        # This is the same upsert contract used by batch_pdf_to_text.py.
        cursor.execute(
            """
            INSERT INTO question_papers (
                pdf_filename, pdf_relative_path, text_file_path, course, subject, academic_year,
                semester, paper_code, exam_year, term, total_pages, ocr_characters,
                extracted_text
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                pdf_filename = VALUES(pdf_filename),
                text_file_path = VALUES(text_file_path),
                course = VALUES(course),
                subject = VALUES(subject),
                academic_year = VALUES(academic_year),
                semester = VALUES(semester),
                paper_code = VALUES(paper_code),
                exam_year = VALUES(exam_year),
                term = VALUES(term),
                total_pages = VALUES(total_pages),
                ocr_characters = VALUES(ocr_characters),
                extracted_text = VALUES(extracted_text),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                pdf_name,
                pdf_relative_path,
                text_relative_path,
                metadata["course"],
                metadata["subject"],
                metadata["academic_year"],
                metadata["semester"],
                metadata["paper_code"],
                metadata["exam_year"],
                metadata["term"],
                total_pages,
                _character_count(extracted_text),
                extracted_text,
            ),
        )

        cursor.execute(
            "SELECT id FROM question_papers WHERE pdf_relative_path = %s",
            (pdf_relative_path,),
        )
        row = cursor.fetchone()
        if row is None:
            raise UploadProcessingError("Paper row could not be verified after insertion.")
        paper_id = int(row[0])

        if questions:
            cursor.executemany(
                """
                INSERT INTO questions (
                    paper_id, question_text, normalized_question,
                    normalized_hash, question_number
                ) VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    question_text = IF(
                        CHAR_LENGTH(question_text) = 0,
                        VALUES(question_text), question_text
                    ),
                    question_number = COALESCE(
                        question_number, VALUES(question_number)
                    )
                """,
                [
                    (
                        paper_id,
                        question["question_text"],
                        question["normalized_question"],
                        question["normalized_hash"],
                        question["question_number"],
                    )
                    for question in questions
                ],
            )

        connection.commit()
        return paper_id, warnings
    except (DatabaseQueryError, DatabaseConfigurationError, UploadProcessingError) as exc:
        logger.error(
            "Paper persistence failed (%s) for relative path %s: %s",
            type(exc).__name__,
            pdf_relative_path,
            _safe_error_detail(exc),
        )
        connection.rollback()
        raise
    except Exception as exc:
        logger.error(
            "Unexpected paper persistence failure (%s) for relative path %s: %s",
            type(exc).__name__,
            pdf_relative_path,
            _safe_error_detail(exc),
        )
        connection.rollback()
        raise DatabaseQueryError("Unable to persist the uploaded paper.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def process_upload(file: FileStorage | None, form: Any) -> dict[str, Any]:
    metadata = _required_metadata(form)
    if file is None or not file.filename:
        raise UploadValidationError("A PDF file is required.")

    safe_name = _safe_pdf_name(file.filename)
    stored_name = safe_name[:180]
    token = uuid.uuid4().hex
    storage_key = f"papers/{token}-{stored_name}"
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary_pdf = INPUT_DIR / f".upload-{token}.part"
    temporary_text = OUTPUT_DIR / f".upload-{token}.txt"
    uploaded_to_storage = False

    try:
        _write_upload(file, temporary_pdf)
        try:
            from pdf_to_text_converter.pdf_to_text import convert_pdf
        except ModuleNotFoundError as exc:
            raise UploadProcessingError(
                f"PDF text extraction dependency is unavailable: {exc.name}. "
                "Install PyMuPDF in the backend environment."
            ) from exc

        try:
            extracted_text, total_pages = convert_pdf(temporary_pdf, temporary_text)
        except ValueError as exc:
            # Scanned PDFs need PaddleOCR. Never load it in the 512 MB hosted worker.
            if "appears to be scanned" in str(exc):
                raise UploadProcessingError(str(exc)) from exc
            raise

        from pyq_questions import extract_questions
        questions = extract_questions(extracted_text)

        # Scanned exam papers can contain a noisy or incomplete embedded OCR
        # layer. If the PDF contains page images, compare it with Tesseract OCR
        # and keep whichever extraction identifies more question choices.
        try:
            from pdf_to_text_converter.pdf_to_text import (
                extract_with_tesseract,
                pdf_has_images,
            )
            if pdf_has_images(temporary_pdf):
                tesseract_text, tesseract_pages = extract_with_tesseract(temporary_pdf)
                tesseract_questions = extract_questions(tesseract_text)
                if len(tesseract_questions) > len(questions):
                    logger.info(
                        "Tesseract improved question extraction from %s to %s questions",
                        len(questions),
                        len(tesseract_questions),
                    )
                    extracted_text = tesseract_text
                    total_pages = tesseract_pages
                    questions = tesseract_questions
        except Exception:
            logger.exception("Tesseract fallback failed; retaining embedded PDF text extraction")

        upload_pdf(storage_key, temporary_pdf.read_bytes())
        uploaded_to_storage = True
        paper_id, warnings = _persist(
            metadata, safe_name, storage_key, None, extracted_text,
            total_pages, questions,
        )
        return {
            "id": paper_id,
            "pdf_filename": safe_name,
            "pdf_relative_path": storage_key,
            "total_pages": total_pages,
            "ocr_characters": _character_count(extracted_text),
            "question_count": len(questions),
            "warnings": warnings,
        }
    except (UploadValidationError, DatabaseConfigurationError, DatabaseQueryError, UploadProcessingError):
        if uploaded_to_storage:
            try:
                delete_pdf(storage_key)
            except StorageError:
                logger.exception("Could not clean up Supabase object %s", storage_key)
        raise
    except StorageError as exc:
        if uploaded_to_storage:
            try:
                delete_pdf(storage_key)
            except StorageError:
                logger.exception("Could not clean up Supabase object %s", storage_key)
        raise UploadProcessingError("PDF storage operation failed. Check Supabase configuration and bucket.") from exc
    except Exception as exc:
        if uploaded_to_storage:
            try:
                delete_pdf(storage_key)
            except StorageError:
                logger.exception("Could not clean up Supabase object %s", storage_key)
        raise UploadProcessingError("PDF processing failed.") from exc
    finally:
        temporary_pdf.unlink(missing_ok=True)
        temporary_text.unlink(missing_ok=True)
