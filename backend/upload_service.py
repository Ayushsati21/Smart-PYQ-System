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


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = BASE_DIR / "input_pdfs"
OUTPUT_DIR = BASE_DIR / "output_text"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
REQUIRED_FIELDS = ("subject", "academic_year", "semester", "exam_year", "term", "paper_code")
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
            "id", "pdf_filename", "pdf_relative_path", "text_file_path", "subject",
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
                pdf_filename, pdf_relative_path, text_file_path, subject, academic_year,
                semester, paper_code, exam_year, term, total_pages, ocr_characters,
                extracted_text
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                pdf_filename = VALUES(pdf_filename),
                text_file_path = VALUES(text_file_path),
                subject = COALESCE(NULLIF(VALUES(subject), ''), subject),
                academic_year = COALESCE(NULLIF(VALUES(academic_year), ''), academic_year),
                semester = COALESCE(NULLIF(VALUES(semester), ''), semester),
                paper_code = COALESCE(NULLIF(VALUES(paper_code), ''), paper_code),
                exam_year = COALESCE(NULLIF(VALUES(exam_year), ''), exam_year),
                term = COALESCE(NULLIF(VALUES(term), ''), term),
                total_pages = VALUES(total_pages),
                ocr_characters = VALUES(ocr_characters),
                extracted_text = VALUES(extracted_text),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                pdf_name,
                pdf_relative_path,
                text_relative_path,
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
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    temporary_pdf = INPUT_DIR / f".upload-{token}.part"
    final_name = _unique_name(safe_name)
    final_pdf = INPUT_DIR / final_name
    temporary_text = OUTPUT_DIR / f".upload-{token}.txt"
    final_text = OUTPUT_DIR / f"{Path(final_name).stem}.txt"
    completed = False

    try:
        _write_upload(file, temporary_pdf)

        # Reuse the existing converter; do not duplicate PaddleOCR setup here.
        try:
            from pdf_to_text_converter.pdf_to_text import convert_pdf
        except ModuleNotFoundError as exc:
            raise UploadProcessingError(
                f"OCR dependency is unavailable: {exc.name}. Install the existing PaddleOCR/PyMuPDF dependencies."
            ) from exc

        extracted_text, total_pages = convert_pdf(temporary_pdf, temporary_text)

        # Reuse the existing numbered-question extraction and normalization.
        from pyq_questions import extract_questions

        questions = extract_questions(extracted_text)
        os.replace(temporary_pdf, final_pdf)
        os.replace(temporary_text, final_text)

        pdf_relative_path = final_pdf.relative_to(BASE_DIR).as_posix()
        text_relative_path = final_text.relative_to(BASE_DIR).as_posix()
        paper_id, warnings = _persist(
            metadata,
            final_name,
            pdf_relative_path,
            text_relative_path,
            extracted_text,
            total_pages,
            questions,
        )
        completed = True
        return {
            "id": paper_id,
            "pdf_filename": final_name,
            "pdf_relative_path": pdf_relative_path,
            "text_file_path": text_relative_path,
            "total_pages": total_pages,
            "ocr_characters": _character_count(extracted_text),
            "question_count": len(questions),
            "warnings": warnings,
        }
    except (UploadValidationError, DatabaseConfigurationError, DatabaseQueryError, UploadProcessingError):
        raise
    except Exception as exc:
        raise UploadProcessingError("PDF processing failed.") from exc
    finally:
        for path in (temporary_pdf, temporary_text):
            path.unlink(missing_ok=True)
        if not completed:
            final_pdf.unlink(missing_ok=True)
            final_text.unlink(missing_ok=True)
