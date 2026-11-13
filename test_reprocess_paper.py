import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.reprocess_service import reprocess_paper
from pyq_questions import extract_questions


class FakeConnection:
    def __init__(self, paper, stored_questions=None, fail_on_insert=False):
        self.paper = paper
        self.stored_questions = stored_questions if stored_questions is not None else []
        self.fail_on_insert = fail_on_insert
        self.cursor_instance = FakeCursor(self)
        self.started = False
        self.committed = False
        self.rolled_back = False
        self.transaction_snapshot = None

    def cursor(self, dictionary=False):
        return self.cursor_instance

    def start_transaction(self):
        self.started = True
        self.transaction_snapshot = list(self.stored_questions)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True
        if self.transaction_snapshot is not None:
            self.stored_questions[:] = self.transaction_snapshot

    def close(self):
        pass


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.executed = []

    def execute(self, query, params=()):
        self.executed.append((query, params))
        if query.startswith("DELETE"):
            self.connection.stored_questions.clear()

    def fetchone(self):
        return self.connection.paper

    def executemany(self, query, rows):
        if self.connection.fail_on_insert:
            raise RuntimeError("simulated insert failure")
        self.connection.stored_questions.extend(rows)

    def close(self):
        pass


class PaperReprocessingTests(unittest.TestCase):
    def _paper_text(self, directory):
        source = Path("output_text/tcs307_endsem_2023_jan.txt")
        destination = Path(directory) / "tcs307_endsem_2023_jan.txt"
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return destination

    @patch("backend.reprocess_service.get_connection")
    def test_success_replaces_only_the_selected_paper_questions(self, get_connection):
        with tempfile.TemporaryDirectory() as directory, patch("backend.reprocess_service.BASE_DIR", Path(directory)):
            text_path = self._paper_text(directory)
            old_questions = [(7, "old", "old", b"old", "7")]
            connection = FakeConnection({"id": 42, "text_file_path": str(text_path)}, old_questions)
            get_connection.return_value = connection

            result = reprocess_paper(42)

            self.assertEqual(result, {"paper_id": 42, "question_count": 15})
            self.assertTrue(connection.committed)
            self.assertFalse(connection.rolled_back)
            self.assertEqual(len(connection.stored_questions), 15)
            self.assertEqual(connection.stored_questions[0][-1], "1(a)")
            self.assertEqual(connection.stored_questions[-1][-1], "5(c)")
            self.assertIn(("DELETE FROM questions WHERE paper_id = %s", (42,)), connection.cursor_instance.executed)

    @patch("backend.reprocess_service.get_connection")
    def test_insert_failure_rolls_back_old_questions(self, get_connection):
        with tempfile.TemporaryDirectory() as directory, patch("backend.reprocess_service.BASE_DIR", Path(directory)):
            text_path = self._paper_text(directory)
            old_questions = [(7, "old", "old", b"old", "7")]
            connection = FakeConnection(
                {"id": 42, "text_file_path": str(text_path)}, old_questions, fail_on_insert=True
            )
            get_connection.return_value = connection

            with self.assertRaisesRegex(RuntimeError, "rolled back"):
                reprocess_paper(42)

            self.assertFalse(connection.committed)
            self.assertTrue(connection.rolled_back)
            self.assertEqual(connection.stored_questions, old_questions)

    @patch("backend.reprocess_service.get_connection")
    def test_repeated_execution_keeps_one_current_question_set(self, get_connection):
        with tempfile.TemporaryDirectory() as directory, patch("backend.reprocess_service.BASE_DIR", Path(directory)):
            text_path = self._paper_text(directory)
            stored_questions = []
            first = FakeConnection({"id": 42, "text_file_path": str(text_path)}, stored_questions)
            second = FakeConnection({"id": 42, "text_file_path": str(text_path)}, stored_questions)
            get_connection.side_effect = [first, second]

            reprocess_paper(42)
            reprocess_paper(42)

            self.assertEqual(len(stored_questions), 15)
            self.assertTrue(first.committed)
            self.assertTrue(second.committed)


if __name__ == "__main__":
    unittest.main()
