"""Admin authentication and database-backed session helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

from flask import current_app, jsonify, request
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from .db import DatabaseConfigurationError, DatabaseQueryError, get_connection


SESSION_COOKIE_NAME = "smart_pyq_admin_session"
SESSION_LIFETIME = timedelta(hours=8)


def _digest(value: str) -> bytes:
    secret = current_app.config.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("FLASK_SECRET_KEY is not configured.")
    return hmac.new(str(secret).encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()


def _admin_from_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {"id": int(row["id"]), "username": row["username"]}


def authenticate_admin(username: str, password: str) -> dict[str, Any] | None:
    """Return an active admin only when the supplied password verifies."""

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, username, password_hash
            FROM admin_users
            WHERE username = %s AND is_active = 1
            """,
            (username,),
        )
        row = cursor.fetchone()
        try:
            password_matches = bool(row and check_password_hash(row["password_hash"], password))
        except (TypeError, ValueError):
            password_matches = False
        return _admin_from_row(row) if password_matches else None
    except Error as exc:
        raise DatabaseQueryError("Unable to authenticate the administrator.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def create_admin_user(username: str, password: str) -> int:
    """Create one active admin using a one-way password hash."""

    if not username.strip():
        raise ValueError("username is required")
    if len(password) < 12:
        raise ValueError("password must contain at least 12 characters")

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, is_active) VALUES (%s, %s, 1)",
            (username.strip(), generate_password_hash(password)),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except Error as exc:
        connection.rollback()
        raise DatabaseQueryError("Unable to create the administrator.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def create_admin_session(admin: dict[str, Any]) -> tuple[str, str]:
    """Create an opaque cookie value and persist its session state in MySQL."""

    session_token = secrets.token_urlsafe(48)
    csrf_value = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + SESSION_LIFETIME
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO auth_sessions (session_token_hash, admin_id, csrf_token_hash, expires_at)
            VALUES (%s, %s, %s, %s)
            """,
            (_digest(session_token), admin["id"], _digest(csrf_value), expires_at),
        )
        connection.commit()
        return session_token, csrf_value
    except Error as exc:
        connection.rollback()
        raise DatabaseQueryError("Unable to create the administrator session.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def get_current_admin_session() -> dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT s.admin_id, a.username, s.csrf_token_hash
            FROM auth_sessions s
            JOIN admin_users a ON a.id = s.admin_id
            WHERE s.session_token_hash = %s
              AND s.expires_at > UTC_TIMESTAMP()
              AND a.is_active = 1
            """,
            (_digest(token),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": int(row["admin_id"]),
            "username": row["username"],
            "csrf_token_hash": row["csrf_token_hash"],
            "session_token": token,
        }
    except Error as exc:
        raise DatabaseQueryError("Unable to retrieve the administrator session.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def refresh_csrf_token(admin_session: dict[str, Any]) -> str:
    csrf_value = secrets.token_urlsafe(32)
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE auth_sessions SET csrf_token_hash = %s WHERE session_token_hash = %s",
            (_digest(csrf_value), _digest(admin_session["session_token"])),
        )
        connection.commit()
        return csrf_value
    except Error as exc:
        connection.rollback()
        raise DatabaseQueryError("Unable to refresh the administrator CSRF token.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def delete_admin_session(session_token: str) -> None:
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM auth_sessions WHERE session_token_hash = %s", (_digest(session_token),))
        connection.commit()
    except Error as exc:
        connection.rollback()
        raise DatabaseQueryError("Unable to end the administrator session.") from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def csrf_is_valid(admin_session: dict[str, Any] | None = None) -> bool:
    admin_session = admin_session or get_current_admin_session()
    supplied = request.headers.get("X-CSRF-Token")
    if not admin_session or not supplied:
        return False
    return hmac.compare_digest(admin_session["csrf_token_hash"], _digest(supplied))


def is_admin_session(admin_session: dict[str, Any] | None = None) -> bool:
    return bool(admin_session or get_current_admin_session())


def admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Require a database-backed admin session and CSRF for mutations."""

    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        if request.method == "OPTIONS":
            return ("", 204)
        try:
            admin_session = get_current_admin_session()
        except (DatabaseConfigurationError, DatabaseQueryError):
            return jsonify({"error": "Unable to verify the administrator session."}), 503
        if not admin_session:
            return jsonify({"error": "Administrator authentication is required."}), 401
        if admin_session.get("role", "admin") != "admin":
            return jsonify({"error": "Admin privileges are required."}), 403
        if request.method not in {"GET", "HEAD"} and not csrf_is_valid(admin_session):
            return jsonify({"error": "A valid CSRF token is required."}), 403
        return view(*args, **kwargs)

    return wrapped

