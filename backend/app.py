"""Flask REST API for public question-paper retrieval and admin uploads."""

from __future__ import annotations

import os
import re
from io import BytesIO

from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename

from .db import (
    DatabaseConfigurationError,
    DatabaseQueryError,
    get_dashboard_summary,
    delete_paper_record,
    get_paper,
    list_papers,
    list_questions,
    list_repeated_questions,
)
from .auth import (
    SESSION_COOKIE_NAME,
    admin_required,
    authenticate_admin,
    create_admin_session,
    csrf_is_valid,
    delete_admin_session,
    get_current_admin_session,
    refresh_csrf_token,
)
from .upload_service import UploadProcessingError, UploadValidationError, process_upload
from .storage import StorageError, delete_pdf, download_pdf


def _safe_error_detail(error: Exception) -> str:
    """Return a bounded error message without leaking configured secrets."""
    detail = str(error)
    for secret_name in ("MYSQL_PASSWORD", "SUPABASE_SERVICE_ROLE_KEY", "FLASK_SECRET_KEY"):
        secret = os.environ.get(secret_name)
        if secret:
            detail = detail.replace(secret, "<redacted>")
    return detail[:500]


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
    AUTH_COOKIE_HTTPONLY=True,
    AUTH_COOKIE_SECURE=os.environ.get("FLASK_ENV", "").casefold() == "production",
    AUTH_COOKIE_SAMESITE=os.environ.get(
        "SESSION_COOKIE_SAMESITE",
        "None" if os.environ.get("FLASK_ENV", "").casefold() == "production" else "Lax",
    ),
)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


class PDFPathError(ValueError):
    """Raised when a stored PDF storage key is invalid."""


def _resolve_paper_pdf(record: dict) -> tuple[str, str]:
    """Validate the Supabase object key stored in TiDB."""

    storage_key = record.get("pdf_relative_path")
    if (
        not isinstance(storage_key, str)
        or not storage_key.startswith("papers/")
        or ".." in storage_key.split("/")
        or len(storage_key) > 255
    ):
        raise PDFPathError("PDF file is unavailable.")
    filename = secure_filename(str(record.get("pdf_filename") or ""))
    if not filename or not filename.lower().endswith(".pdf"):
        raise PDFPathError("PDF file is unavailable.")
    return storage_key, filename


def _serve_paper_pdf(paper_id: int, *, as_attachment: bool):
    record = get_paper(paper_id)
    if record is None:
        return jsonify({"error": "Question paper not found."}), 404
    try:
        storage_key, download_name = _resolve_paper_pdf(record)
        pdf_bytes = download_pdf(storage_key)
    except PDFPathError:
        return jsonify({"error": "PDF file is unavailable."}), 404
    except StorageError:
        app.logger.exception("Supabase PDF retrieval failed for paper %s", paper_id)
        return jsonify({"error": "PDF storage is temporarily unavailable."}), 503
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=as_attachment,
        download_name=download_name,
        conditional=False,
    )


@app.after_request
def add_development_cors(response):
    """Allow the separately served frontend to call the local API in development."""

    allowed_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5500")
    request_origin = request.headers.get("Origin")
    if request_origin and request_origin != allowed_origin:
        return response
    response.headers["Access-Control-Allow-Origin"] = allowed_origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRF-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, POST, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.post("/api/auth/login")
def auth_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = payload.get("password")
    if not username or not isinstance(password, str) or not password:
        return jsonify({"error": "Username and password are required."}), 400
    try:
        administrator = authenticate_admin(username, password)
    except (DatabaseConfigurationError, DatabaseQueryError) as exc:
        return jsonify({"error": str(exc)}), 503
    if administrator is None:
        return jsonify({"error": "Invalid administrator credentials."}), 401
    try:
        session_token, csrf_value = create_admin_session(administrator)
    except (DatabaseConfigurationError, DatabaseQueryError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 503
    response = jsonify({"admin": administrator, "csrf_token": csrf_value})
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        httponly=app.config["AUTH_COOKIE_HTTPONLY"],
        secure=app.config["AUTH_COOKIE_SECURE"],
        samesite=app.config["AUTH_COOKIE_SAMESITE"],
        max_age=8 * 60 * 60,
        path="/",
    )
    return response


@app.post("/api/auth/logout")
def auth_logout():
    try:
        current = get_current_admin_session()
        if current and not csrf_is_valid(current):
            return jsonify({"error": "A valid CSRF token is required."}), 403
        if current:
            delete_admin_session(current["session_token"])
    except (DatabaseConfigurationError, DatabaseQueryError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 503
    response = jsonify({"message": "Logged out."})
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@app.get("/api/auth/me")
def auth_me():
    try:
        current = get_current_admin_session()
    except (DatabaseConfigurationError, DatabaseQueryError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 503
    if not current:
        return jsonify({"error": "Administrator authentication is required."}), 401
    try:
        csrf_value = refresh_csrf_token(current)
    except (DatabaseConfigurationError, DatabaseQueryError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 503
    return jsonify(
        {
            "admin": {"id": current["id"], "username": current["username"]},
            "csrf_token": csrf_value,
        }
    )


@app.get("/api/papers")
def papers():
    try:
        data = list_papers(
            {
                key: request.args.get(key, "").strip()
                for key in ("q", "subject", "academic_year", "exam_year", "term")
                if request.args.get(key, "").strip()
            }
        )
        return jsonify({"data": data, "count": len(data)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except DatabaseConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except DatabaseQueryError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("Unexpected error while listing papers")
        return jsonify({"error": "Unexpected server error."}), 500


@app.get("/api/dashboard/summary")
def dashboard_summary():
    """Return live aggregate statistics without requiring student authentication."""

    try:
        return jsonify(get_dashboard_summary())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except (DatabaseConfigurationError, DatabaseQueryError) as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("Unexpected error while retrieving dashboard summary")
        return jsonify({"error": "Unexpected server error."}), 500


@app.get("/api/papers/<int:paper_id>")
def paper(paper_id: int):
    try:
        record = get_paper(paper_id)
        if record is None:
            return jsonify({"error": "Question paper not found."}), 404
        return jsonify(record)
    except DatabaseConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except DatabaseQueryError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("Unexpected error while retrieving paper %s", paper_id)
        return jsonify({"error": "Unexpected server error."}), 500


@app.delete("/api/papers/<int:paper_id>")
@admin_required
def delete_paper(paper_id: int):
    """Delete a paper and its extracted questions; remove its stored PDF afterward."""
    try:
        record = get_paper(paper_id)
        if record is None:
            return jsonify({"error": "Question paper not found."}), 404
        storage_key, _ = _resolve_paper_pdf(record)
        if not delete_paper_record(paper_id):
            return jsonify({"error": "Question paper not found."}), 404
        try:
            delete_pdf(storage_key)
        except StorageError:
            app.logger.exception("Paper %s was deleted from MySQL but its PDF cleanup failed", paper_id)
            return jsonify({
                "message": "Paper and questions deleted from the database, but PDF cleanup failed.",
                "storage_cleanup": "failed",
            }), 200
        return jsonify({"message": "Paper, extracted questions, and stored PDF deleted."})
    except PDFPathError:
        return jsonify({"error": "Stored PDF path is invalid; paper was not deleted."}), 409
    except (DatabaseConfigurationError, DatabaseQueryError) as exc:
        app.logger.exception("Database failure while deleting paper %s", paper_id)
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("Unexpected error while deleting paper %s", paper_id)
        return jsonify({"error": "Unexpected server error while deleting the paper."}), 500


@app.get("/api/papers/<int:paper_id>/pdf")
def paper_pdf(paper_id: int):
    """Serve the stored PDF for inline browser viewing."""

    try:
        return _serve_paper_pdf(paper_id, as_attachment=False)
    except DatabaseConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except DatabaseQueryError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("Unexpected error while serving PDF for paper %s", paper_id)
        return jsonify({"error": "Unexpected server error."}), 500


@app.get("/api/papers/<int:paper_id>/download")
def download_paper(paper_id: int):
    """Download the stored PDF as an attachment."""

    try:
        return _serve_paper_pdf(paper_id, as_attachment=True)
    except DatabaseConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except DatabaseQueryError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("Unexpected error while downloading PDF for paper %s", paper_id)
        return jsonify({"error": "Unexpected server error."}), 500


@app.get("/api/questions")
def questions():
    """Return extracted questions joined with their question-paper metadata."""

    try:
        filters = {
            key: request.args.get(key, "").strip()
            for key in ("paper_id", "subject", "exam_year", "question_number", "q")
            if request.args.get(key, "").strip()
        }
        data = list_questions(filters)
        return jsonify({"data": data, "count": len(data)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except DatabaseConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except DatabaseQueryError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("Unexpected error while listing extracted questions")
        return jsonify({"error": "Unexpected server error."}), 500


@app.get("/api/repeated-questions")
def repeated_questions():
    """Return exact and semantically similar question matches across papers."""
    try:
        filters = {
            key: request.args.get(key, "").strip()
            for key in ("subject", "exam_year", "min_frequency")
            if request.args.get(key, "").strip()
        }
        data = list_repeated_questions(filters)
        return jsonify({"data": data, "count": len(data)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except DatabaseConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except DatabaseQueryError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("Unexpected error while listing repeated questions")
        return jsonify({"error": "Unexpected server error."}), 500


@app.post("/api/papers")
@admin_required
def upload_paper():
    """Accept one PDF and persist its OCR result and extracted questions."""

    try:
        uploaded_file = request.files.get("pdf") or request.files.get("file")
        result = process_upload(uploaded_file, request.form)
        return jsonify({"message": "Paper uploaded and processed.", "data": result}), 201
    except UploadValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except (DatabaseConfigurationError, DatabaseQueryError) as exc:
        app.logger.error(
            "Paper upload database failure (%s): %s",
            type(exc).__name__,
            _safe_error_detail(exc),
        )
        message = (
            "Database configuration is incomplete."
            if isinstance(exc, DatabaseConfigurationError)
            else "Database operation failed. Check the Flask server logs."
        )
        return jsonify({"error": message}), 503
    except UploadProcessingError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception:
        app.logger.exception("Unexpected error while uploading paper")
        return jsonify({"error": "Unexpected server error while processing the upload."}), 500


@app.get("/api/papers/")
def paper_collection_slash():
    """Keep the collection URL explicit; one-paper retrieval uses /api/papers/<id>."""

    return papers()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=False,
    )
