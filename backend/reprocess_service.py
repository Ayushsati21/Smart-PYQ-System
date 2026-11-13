"""Safe, explicit reprocessing of one stored paper's extracted questions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .db import DatabaseConfigurationError, DatabaseQueryError, get_connection


BASE_DIR = Path(__file__).resolve().parents[1]


class PaperReprocessingError(RuntimeError):
    """Raised when one paper cannot be reprocessed safely."""


def _stored_text_path(text_file_path: str | None) -> Path:
    if not text_file_path:
        raise PaperReprocessingError("The paper has no stored OCR text file path.")

    candidate = Path(text_file_path)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(BASE_DIR.resolve())
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise PaperReprocessingError(
            "The stored OCR text file is missing or outside the project directory."
        ) from exc
    if not resolved.is_file():
        raise PaperReprocessingError("The stored OCR text path is not a file.")
    return resolved


def _deduplicate_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[bytes, dict[str, Any]] = {}
    for question in questions:
        unique.setdefault(question["normalized_hash"], question)
    return list(unique.values())


def reprocess_paper(paper_id: int) -> dict[str, int]:
    """Replace extracted questions for exactly one existing paper in a transaction."""

    if not isinstance(paper_id, int) or paper_id < 1:
        raise PaperReprocessingError("paper_id must be a positive integer.")

    connection = None
    cursor = None
    transaction_started = False
    try:
        connection = get_connection()
        connection.start_transaction()
        transaction_started = True
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, text_file_path FROM question_papers WHERE id = %s",
            (paper_id,),
        )
        paper = cursor.fetchone()
        if paper is None:
            raise PaperReprocessingError(f"No question paper exists with id {paper_id}.")

        text_path = _stored_text_path(paper.get("text_file_path"))

        from pyq_questions import extract_questions

        extracted_text = text_path.read_text(encoding="utf-8")
        questions = _deduplicate_questions(extract_questions(extracted_text))

        cursor.execute("DELETE FROM questions WHERE paper_id = %s", (paper_id,))
        if questions:
            cursor.executemany(
                """
                INSERT INTO questions (
                    paper_id, question_text, normalized_question,
                    normalized_hash, question_number
                ) VALUES (%s, %s, %s, %s, %s)
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
        return {"paper_id": paper_id, "question_count": len(questions)}
    except PaperReprocessingError:
        if transaction_started and connection is not None:
            connection.rollback()
        raise
    except (DatabaseConfigurationError, DatabaseQueryError) as exc:
        if transaction_started and connection is not None:
            connection.rollback()
        raise PaperReprocessingError("Database access failed while reprocessing the paper.") from exc
    except Exception as exc:
        if transaction_started and connection is not None:
            connection.rollback()
        raise PaperReprocessingError("Reprocessing failed; the transaction was rolled back.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
