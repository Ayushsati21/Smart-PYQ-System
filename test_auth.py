import io
import unittest
from unittest.mock import patch

from backend.app import app


class AuthenticationRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-only-secret")
        self.client = app.test_client()

    @patch("backend.app.create_admin_session", return_value=("opaque-session", "csrf-token"))
    @patch("backend.app.authenticate_admin")
    def test_successful_admin_login_creates_session_and_csrf_token(self, authenticate, create_session):
        authenticate.return_value = {"id": 7, "username": "admin"}

        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["admin"]["username"], "admin")
        self.assertTrue(response.get_json()["csrf_token"])
        self.assertIn("smart_pyq_admin_session=opaque-session", response.headers["Set-Cookie"])
        create_session.assert_called_once_with({"id": 7, "username": "admin"})

    @patch("backend.app.authenticate_admin", return_value=None)
    def test_incorrect_password_is_rejected(self, authenticate):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Invalid administrator credentials.")

    @patch("backend.app.authenticate_admin", return_value=None)
    def test_inactive_admin_is_rejected(self, authenticate):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "inactive", "password": "correct-password"},
        )

        self.assertEqual(response.status_code, 401)

    def _set_admin_session(self, role="admin"):
        self.admin_session = {
            "id": 7,
            "username": "admin",
            "session_token": "opaque-session",
            "csrf_token_hash": b"hash",
            "role": role,
        }

    @patch("backend.app.process_upload", return_value={"id": 10, "question_count": 1})
    def test_upload_requires_admin_authentication(self, process_upload):
        response = self.client.post(
            "/api/papers",
            data={"pdf": (io.BytesIO(b"%PDF-test"), "paper.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 401)
        process_upload.assert_not_called()

    @patch("backend.auth.csrf_is_valid", return_value=True)
    @patch("backend.auth.get_current_admin_session")
    @patch("backend.app.process_upload", return_value={"id": 10, "question_count": 1})
    def test_authenticated_non_admin_cannot_upload(self, process_upload, current_session, csrf):
        self._set_admin_session(role="student")
        current_session.return_value = self.admin_session

        response = self.client.post(
            "/api/papers",
            data={"pdf": (io.BytesIO(b"%PDF-test"), "paper.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 403)
        process_upload.assert_not_called()

    @patch("backend.auth.csrf_is_valid", return_value=True)
    @patch("backend.auth.get_current_admin_session")
    @patch("backend.app.process_upload", return_value={"id": 10, "question_count": 1})
    def test_authenticated_admin_can_upload_with_csrf_token(self, process_upload, current_session, csrf):
        self._set_admin_session()
        current_session.return_value = self.admin_session

        response = self.client.post(
            "/api/papers",
            data={"pdf": (io.BytesIO(b"%PDF-test"), "paper.pdf")},
            content_type="multipart/form-data",
            headers={"X-CSRF-Token": "csrf-test-token"},
        )

        self.assertEqual(response.status_code, 201)
        process_upload.assert_called_once()

    @patch("backend.auth.csrf_is_valid", return_value=False)
    @patch("backend.auth.get_current_admin_session")
    @patch("backend.app.process_upload")
    def test_upload_rejects_missing_csrf_token(self, process_upload, current_session, csrf):
        self._set_admin_session()
        current_session.return_value = self.admin_session

        response = self.client.post(
            "/api/papers",
            data={"pdf": (io.BytesIO(b"%PDF-test"), "paper.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 403)
        process_upload.assert_not_called()

    @patch("backend.app.list_papers", return_value=[{"id": 1}])
    def test_public_student_api_is_available_without_login(self, list_papers):
        response = self.client.get("/api/papers")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 1)
        list_papers.assert_called_once_with({})

    @patch("backend.app.list_papers", return_value=[])
    def test_cors_rejects_unconfigured_origins(self, list_papers):
        response = self.client.get("/api/papers", headers={"Origin": "https://untrusted.example"})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    @patch("backend.app.delete_admin_session")
    @patch("backend.app.csrf_is_valid", return_value=True)
    @patch("backend.app.get_current_admin_session")
    def test_logout_clears_admin_session(self, current_session, csrf, delete_session):
        self._set_admin_session()
        current_session.return_value = self.admin_session

        response = self.client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": "csrf-test-token"},
        )

        self.assertEqual(response.status_code, 200)
        delete_session.assert_called_once_with("opaque-session")

    @patch("backend.app.get_current_admin_session", return_value=None)
    def test_expired_session_is_rejected(self, current_session):
        self.client.set_cookie("smart_pyq_admin_session", "expired-token")
        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
