import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.app import app


class PaperDetailsRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    @patch("backend.app.get_paper")
    def test_each_database_id_returns_its_own_paper(self, get_paper):
        papers = {
            11: {"id": 11, "pdf_filename": "tcs307_endsem_2023_jan.pdf", "subject": "OOP in C++", "exam_year": 2023},
            12: {"id": 12, "pdf_filename": "tcs307_endsem_2024_jan_3.pdf", "subject": "OOP in C++", "exam_year": 2024},
        }
        get_paper.side_effect = papers.get

        first = self.client.get("/api/papers/11")
        second = self.client.get("/api/papers/12")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.get_json()["id"], 11)
        self.assertEqual(first.get_json()["pdf_filename"], "tcs307_endsem_2023_jan.pdf")
        self.assertEqual(second.get_json()["id"], 12)
        self.assertEqual(second.get_json()["pdf_filename"], "tcs307_endsem_2024_jan_3.pdf")
        self.assertEqual(get_paper.call_args_list[0].args, (11,))
        self.assertEqual(get_paper.call_args_list[1].args, (12,))

    @patch("backend.app.get_paper", return_value=None)
    def test_unknown_database_id_is_not_replaced_with_another_paper(self, get_paper):
        response = self.client.get("/api/papers/999999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(get_paper.call_args.args, (999999,))

    def _paper_record(self, pdf_path, filename="paper.pdf"):
        return {
            "id": 10,
            "pdf_filename": filename,
            "pdf_relative_path": pdf_path,
        }

    @patch("backend.app.get_paper")
    def test_pdf_endpoint_serves_the_requested_paper(self, get_paper):
        with TemporaryDirectory() as directory:
            storage = Path(directory) / "input_pdfs"
            storage.mkdir()
            with patch("backend.app.INPUT_DIR", storage):
                pdf = storage / "paper.pdf"
                pdf.write_bytes(b"%PDF-test-content")
                get_paper.return_value = self._paper_record("input_pdfs/paper.pdf")

                response = self.client.get("/api/papers/10/pdf")
                body = response.get_data()
                response.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("inline", response.headers["Content-Disposition"])
        self.assertEqual(body, b"%PDF-test-content")

    @patch("backend.app.get_paper")
    def test_download_endpoint_returns_an_attachment_with_database_filename(self, get_paper):
        with TemporaryDirectory() as directory:
            storage = Path(directory) / "input_pdfs"
            storage.mkdir()
            with patch("backend.app.INPUT_DIR", storage):
                pdf = storage / "stored-name.pdf"
                pdf.write_bytes(b"%PDF-download")
                get_paper.return_value = self._paper_record(
                    "input_pdfs/stored-name.pdf", "download-name.pdf"
                )

                response = self.client.get("/api/papers/10/download")
                response.get_data()
                response.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertIn("download-name.pdf", response.headers["Content-Disposition"])

    @patch("backend.app.get_paper", return_value=None)
    def test_pdf_endpoint_returns_json_404_for_unknown_paper(self, get_paper):
        response = self.client.get("/api/papers/999999/pdf")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "Question paper not found."})

    @patch("backend.app.get_paper")
    def test_pdf_endpoint_returns_json_404_when_file_is_missing(self, get_paper):
        with TemporaryDirectory() as directory:
            storage = Path(directory) / "input_pdfs"
            storage.mkdir()
            with patch("backend.app.INPUT_DIR", storage):
                get_paper.return_value = self._paper_record("input_pdfs/missing.pdf")

                response = self.client.get("/api/papers/10/pdf")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "PDF file is unavailable."})

    @patch("backend.app.get_paper")
    def test_pdf_endpoint_rejects_paths_outside_storage_directory(self, get_paper):
        with TemporaryDirectory() as directory:
            storage = Path(directory) / "input_pdfs"
            storage.mkdir()
            with patch("backend.app.INPUT_DIR", storage):
                outside = Path(directory) / "escape.pdf"
                outside.write_bytes(b"%PDF-should-not-be-served")
                get_paper.return_value = self._paper_record("input_pdfs/../escape.pdf")

                response = self.client.get("/api/papers/10/pdf")

                outside.unlink(missing_ok=True)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "PDF file is unavailable."})


if __name__ == "__main__":
    unittest.main()
