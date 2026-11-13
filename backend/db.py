"""MySQL access for the Smart PYQ Flask API.

This module deliberately owns all database configuration and SQL. Credentials
must be provided through environment variables; they are never sent to the
frontend.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

import mysql.connector
from mysql.connector import Error

from .repeated_questions import DEFAULT_SIMILARITY_THRESHOLD, find_repeated_question_pairs


class DatabaseConfigurationError(RuntimeError):
    """Raised when the API cannot safely build a database connection."""


class DatabaseQueryError(RuntimeError):
    """Raised when a database query cannot be completed."""


def _database_config() -> dict[str, Any]:
    password = os.environ.get("MYSQL_PASSWORD")
    if password is None or password == "":
        raise DatabaseConfigurationError(
            "MYSQL_PASSWORD is not set. Configure database credentials before starting the API."
        )

    try:
        port = int(os.environ.get("MYSQL_PORT", "3306"))
        timeout = int(os.environ.get("MYSQL_CONNECT_TIMEOUT", "5"))
    except ValueError as exc:
        raise DatabaseConfigurationError("MYSQL_PORT and MYSQL_CONNECT_TIMEOUT must be integers.") from exc

    config = {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": port,
        "database": os.environ.get("MYSQL_DATABASE", "smart_pyq_db"),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": password,
        "connection_timeout": timeout,
    }
    ssl_ca = os.environ.get("MYSQL_SSL_CA")
    if ssl_ca:
        config.update(
            ssl_ca=ssl_ca,
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )
    return config


def get_connection():
    """Open a MySQL connection using process environment variables."""

    try:
        return mysql.connector.connect(**_database_config())
    except DatabaseConfigurationError:
        raise
    except Error as exc:
        raise DatabaseQueryError("Unable to connect to the configured MySQL database.") from exc


PAPER_COLUMNS = (
    "id, pdf_filename, pdf_relative_path, text_file_path, subject, "
    "academic_year, semester, paper_code, exam_year, term, total_pages, ocr_characters, "
    "created_at, updated_at"
)

QUESTION_COLUMNS = (
    "q.id, q.paper_id, q.question_number, q.question_text, "
    "q.normalized_question, q.created_at, "
    "qp.pdf_filename AS paper_filename, qp.subject AS paper_subject, "
    "qp.academic_year AS paper_academic_year, qp.semester AS paper_semester, "
    "qp.paper_code AS paper_code, qp.exam_year AS paper_exam_year, "
    "qp.term AS paper_term"
)


def _serialize(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _paper_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize(value) for key, value in row.items()}


def list_papers(filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
    filters = filters or {}
    clauses: list[str] = []
    params: list[Any] = []

    if filters.get("subject"):
        clauses.append("subject = %s")
        params.append(filters["subject"])
    if filters.get("academic_year"):
        clauses.append("academic_year = %s")
        params.append(filters["academic_year"])
    if filters.get("exam_year"):
        try:
            params.append(int(filters["exam_year"]))
        except ValueError as exc:
            raise ValueError("exam_year must be an integer.") from exc
        clauses.append("exam_year = %s")
    if filters.get("term"):
        clauses.append("term = %s")
        params.append(filters["term"])
    if filters.get("q"):
        clauses.append("(pdf_filename LIKE %s OR subject LIKE %s)")
        search = f"%{filters['q']}%"
        params.extend([search, search])

    query = f"SELECT {PAPER_COLUMNS} FROM question_papers"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY exam_year DESC, pdf_filename ASC"

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return [_paper_from_row(row) for row in cursor.fetchall()]
    except (Error, KeyError) as exc:
        raise DatabaseQueryError("Unable to retrieve question papers.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def get_paper(paper_id: int) -> dict[str, Any] | None:
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            f"SELECT {PAPER_COLUMNS} FROM question_papers WHERE id = %s",
            (paper_id,),
        )
        row = cursor.fetchone()
        return _paper_from_row(row) if row else None
    except (Error, KeyError) as exc:
        raise DatabaseQueryError("Unable to retrieve the requested question paper.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def get_dashboard_summary(recent_limit: int = 5) -> dict[str, Any]:
    """Return read-only aggregate data for the public/admin dashboard."""

    try:
        recent_limit = max(1, min(int(recent_limit), 20))
    except (TypeError, ValueError) as exc:
        raise ValueError("recent_limit must be an integer.") from exc

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total_papers FROM question_papers")
        total_papers = int(cursor.fetchone()["total_papers"])
        cursor.execute("SELECT COUNT(*) AS total_questions FROM questions")
        total_questions = int(cursor.fetchone()["total_questions"])
        cursor.execute(
            "SELECT COALESCE(NULLIF(TRIM(qp.subject), ''), 'Uncategorised') AS subject, "
            "COUNT(DISTINCT qp.id) AS paper_count, COUNT(q.id) AS question_count "
            "FROM question_papers qp LEFT JOIN questions q ON q.paper_id = qp.id "
            "GROUP BY COALESCE(NULLIF(TRIM(qp.subject), ''), 'Uncategorised') "
            "ORDER BY paper_count DESC, subject ASC"
        )
        subjects = [
            {key: _serialize(value) for key, value in row.items()}
            for row in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT qp.id, qp.pdf_filename, qp.subject, qp.exam_year, qp.total_pages, "
            "qp.ocr_characters, qp.created_at, COUNT(q.id) AS question_count "
            "FROM question_papers qp LEFT JOIN questions q ON q.paper_id = qp.id "
            "GROUP BY qp.id, qp.pdf_filename, qp.subject, qp.exam_year, qp.total_pages, "
            "qp.ocr_characters, qp.created_at "
            "ORDER BY qp.created_at DESC, qp.id DESC LIMIT %s",
            (recent_limit,),
        )
        recent = [
            {key: _serialize(value) for key, value in row.items()}
            for row in cursor.fetchall()
        ]
        return {
            "total_papers": total_papers,
            "total_questions": total_questions,
            "subject_distribution": subjects,
            "recent_papers": recent,
        }
    except (Error, KeyError) as exc:
        raise DatabaseQueryError("Unable to retrieve dashboard summary.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def list_questions(filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Return extracted questions joined with their parent paper metadata."""

    filters = filters or {}
    clauses: list[str] = []
    params: list[Any] = []

    if filters.get("paper_id"):
        try:
            params.append(int(filters["paper_id"]))
        except ValueError as exc:
            raise ValueError("paper_id must be an integer.") from exc
        clauses.append("q.paper_id = %s")
    if filters.get("subject"):
        clauses.append("qp.subject = %s")
        params.append(filters["subject"])
    if filters.get("exam_year"):
        try:
            params.append(int(filters["exam_year"]))
        except ValueError as exc:
            raise ValueError("exam_year must be an integer.") from exc
        clauses.append("qp.exam_year = %s")
    if filters.get("question_number"):
        clauses.append("q.question_number = %s")
        params.append(filters["question_number"])
    if filters.get("q"):
        clauses.append("(q.question_text LIKE %s OR qp.pdf_filename LIKE %s)")
        search = f"%{filters['q']}%"
        params.extend([search, search])

    query = (
        f"SELECT {QUESTION_COLUMNS} FROM questions q "
        "JOIN question_papers qp ON qp.id = q.paper_id"
    )
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY qp.exam_year DESC, qp.pdf_filename ASC, q.question_number ASC, q.id ASC"

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return [{key: _serialize(value) for key, value in row.items()} for row in cursor.fetchall()]
    except (Error, KeyError) as exc:
        raise DatabaseQueryError("Unable to retrieve extracted questions.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def _similarity_threshold() -> float:
    raw_value = os.environ.get("REPEATED_QUESTION_SIMILARITY_THRESHOLD", str(DEFAULT_SIMILARITY_THRESHOLD))
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError("REPEATED_QUESTION_SIMILARITY_THRESHOLD must be a number between 0 and 1.") from exc
    if not 0.0 <= value <= 1.0:
        raise ValueError("REPEATED_QUESTION_SIMILARITY_THRESHOLD must be between 0 and 1.")
    return value


def list_repeated_questions(filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Return exact and semantically similar question pairs across papers."""

    filters = filters or {}
    clauses: list[str] = []
    params: list[Any] = []
    if filters.get("subject"):
        clauses.append("qp.subject = %s")
        params.append(filters["subject"])
    requested_exam_year = None
    if filters.get("exam_year"):
        try:
            requested_exam_year = int(filters["exam_year"])
        except ValueError as exc:
            raise ValueError("exam_year must be an integer.") from exc
    try:
        minimum_frequency = int(filters.get("min_frequency", 2))
    except ValueError as exc:
        raise ValueError("min_frequency must be an integer.") from exc
    if minimum_frequency < 2:
        raise ValueError("min_frequency must be at least 2.")

    query = (
        "SELECT q.id AS question_id, q.paper_id, q.question_text, "
        "q.normalized_question, q.normalized_hash, qp.pdf_filename AS paper_filename, "
        "qp.subject, qp.exam_year "
        "FROM questions q JOIN question_papers qp ON qp.id = q.paper_id"
    )
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY q.paper_id ASC, q.id ASC"

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        rows = [{key: _serialize(value) for key, value in row.items()} for row in cursor.fetchall()]
        pairs = find_repeated_question_pairs(
            rows,
            similarity_threshold=_similarity_threshold(),
            minimum_frequency=minimum_frequency,
        )
        if requested_exam_year is not None:
            pairs = [pair for pair in pairs if requested_exam_year in pair["exam_years"]]
        return pairs
    except (Error, KeyError, TypeError, ValueError) as exc:
        raise DatabaseQueryError("Unable to retrieve repeated questions.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
