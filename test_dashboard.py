import unittest
from unittest.mock import patch

from backend.app import app


class DashboardSummaryRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    @patch("backend.app.get_dashboard_summary")
    def test_dashboard_summary_returns_live_aggregate_shape_without_login(self, get_summary):
        get_summary.return_value = {
            "total_papers": 2,
            "total_questions": 30,
            "subject_distribution": [
                {"subject": "OOP in C++", "paper_count": 2, "question_count": 30}
            ],
            "recent_papers": [{"id": 11, "pdf_filename": "oop-2024.pdf", "question_count": 15}],
        }

        response = self.client.get("/api/dashboard/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total_papers"], 2)
        self.assertEqual(response.get_json()["recent_papers"][0]["id"], 11)
        get_summary.assert_called_once_with()

    @patch("backend.app.get_dashboard_summary", side_effect=RuntimeError("database unavailable"))
    def test_dashboard_summary_does_not_expose_unexpected_error_details(self, _get_summary):
        response = self.client.get("/api/dashboard/summary")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"error": "Unexpected server error."})


if __name__ == "__main__":
    unittest.main()
