import unittest
from unittest.mock import Mock

from backend.backfill_data_structure import (
    TARGET_PAPERS,
    build_plans,
    execute_repair,
    format_dry_run,
    validate_paper_ids,
)
from backend.reprocess_service import _deduplicate_questions
from pyq_questions import extract_questions


class DataStructureBackfillTests(unittest.TestCase):
    def test_allowlist_requires_exactly_the_four_approved_ids(self):
        self.assertEqual(validate_paper_ids([2, 3, 4, 5]), (2, 3, 4, 5))
        with self.assertRaisesRegex(ValueError, "Only paper IDs"):
            validate_paper_ids([2, 3, 4, 10])
        with self.assertRaisesRegex(ValueError, "Only paper IDs"):
            validate_paper_ids([2, 3, 4])

    def test_dry_run_uses_existing_ocr_and_reports_expected_counts(self):
        plans = build_plans()
        self.assertEqual([plan.paper_id for plan in plans], [2, 3, 4, 5])
        self.assertEqual([plan.insertion_count for plan in plans], [13, 15, 15, 15])
        report = format_dry_run(plans)
        self.assertIn("DRY RUN ONLY: no database statements were executed.", report)
        self.assertIn("Paper ID 2", report)
        self.assertIn("Expected total insertions: 58", report)

    def test_normalized_hash_deduplication_keeps_one_question(self):
        questions = extract_questions("Q1. Define a stack.\nQ2. define a stack.")
        unique = _deduplicate_questions(questions)
        self.assertEqual(len(questions), 2)
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0]["normalized_hash"], questions[0]["normalized_hash"])

    def test_execute_repair_calls_only_planned_ids_and_checks_counts(self):
        plans = build_plans()
        reprocess = Mock(
            side_effect=[
                {"paper_id": 2, "question_count": 13},
                {"paper_id": 3, "question_count": 15},
                {"paper_id": 4, "question_count": 15},
                {"paper_id": 5, "question_count": 15},
            ]
        )
        results = execute_repair(plans, reprocess=reprocess)
        self.assertEqual([result["paper_id"] for result in results], [2, 3, 4, 5])
        self.assertEqual(reprocess.call_args_list, [((2,),), ((3,),), ((4,),), ((5,),)])

    def test_execute_repair_stops_on_count_mismatch(self):
        plans = build_plans()
        reprocess = Mock(side_effect=[{"paper_id": 2, "question_count": 99}])
        with self.assertRaisesRegex(RuntimeError, "expected 13 questions"):
            execute_repair(plans, reprocess=reprocess)
        self.assertEqual(reprocess.call_count, 1)


if __name__ == "__main__":
    unittest.main()
