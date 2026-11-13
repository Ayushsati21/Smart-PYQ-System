import unittest
from unittest.mock import patch
from pathlib import Path

from backend.app import app
from backend.db import list_repeated_questions
from backend.repeated_questions import _component_sizes, find_repeated_question_pairs
from pyq_questions import extract_questions, normalize_question, question_hash


def question(question_id, paper_id, filename, text, subject="OOP", exam_year=2024):
    normalized = normalize_question(text)
    return {
        "question_id": question_id,
        "paper_id": paper_id,
        "question_text": text,
        "normalized_question": normalized,
        "normalized_hash": question_hash(normalized),
        "paper_filename": filename,
        "subject": subject,
        "exam_year": exam_year,
    }


class RepeatedQuestionMatchingTests(unittest.TestCase):
    def test_exact_matches_are_preserved_and_include_pair_metadata(self):
        rows = [
            question(1, 10, "oop-2024.pdf", "Explain inheritance and polymorphism with suitable examples."),
            question(2, 11, "oop-2023.pdf", "Explain inheritance and polymorphism with suitable examples."),
        ]

        result = find_repeated_question_pairs(rows)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["match_type"], "Exact")
        self.assertEqual(result[0]["similarity_percentage"], 100.0)
        self.assertEqual({result[0]["first_paper_id"], result[0]["second_paper_id"]}, {10, 11})
        self.assertEqual(result[0]["paper_filenames"], ["oop-2024.pdf", "oop-2023.pdf"])

    def test_differently_worded_similar_questions_match_at_eighty_percent(self):
        rows = [
            question(1, 10, "oop-2024.pdf", "Explain the difference between inheritance and polymorphism in object oriented programming with examples."),
            question(2, 11, "oop-2023.pdf", "Describe how inheritance differs from polymorphism in object oriented programming, with examples."),
        ]

        result = find_repeated_question_pairs(rows, similarity_threshold=0.80)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["match_type"], "Similar")
        self.assertGreaterEqual(result[0]["similarity_percentage"], 80.0)

    def test_similarity_threshold_boundary_is_respected(self):
        rows = [
            question(1, 10, "oop-2024.pdf", "Explain inheritance and polymorphism in object oriented programming with examples."),
            question(2, 11, "oop-2023.pdf", "Describe how inheritance differs from polymorphism in object oriented programming, with examples."),
        ]
        result = find_repeated_question_pairs(rows)
        score = result[0]["similarity_percentage"] / 100

        self.assertTrue(find_repeated_question_pairs(rows, similarity_threshold=score - 0.001))
        self.assertFalse(find_repeated_question_pairs(rows, similarity_threshold=score + 0.001))

    def test_actual_oop_topic_variations_match_without_lowering_threshold(self):
        topic_pairs = [
            ("Discuss the importance of namespaces.", "Discuss the importance of namespaces and resolving conflicts using namespaces."),
            ("Explain the diamond problem and its solution.", "Explain the diamond problem, solution, advantages and drawbacks."),
            ("Explain virtual base class and virtual destructor.", "Explain normal vs virtual destructors."),
        ]
        for first_text, second_text in topic_pairs:
            with self.subTest(first_text=first_text):
                result = find_repeated_question_pairs([
                    question(1, 10, "oop-2023.pdf", first_text, exam_year=2023),
                    question(2, 11, "oop-2024.pdf", second_text, exam_year=2024),
                ])
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["match_type"], "Similar")
                self.assertGreaterEqual(result[0]["similarity_percentage"], 80.0)

    def test_actual_15_by_15_fixture_checks_all_225_cross_paper_pairs(self):
        def file_rows(path, paper_id, year):
            rows = []
            for question_id, extracted in enumerate(
                extract_questions(Path(path).read_text(encoding="utf-8")), start=1
            ):
                rows.append(question(
                    question_id,
                    paper_id,
                    Path(path).name,
                    extracted["question_text"],
                    exam_year=year,
                ))
            return rows

        first = file_rows("output_text/tcs307_endsem_2023_jan.txt", 10, 2023)
        second = file_rows("output_text/tcs307_endsem_2024_jan_3.txt", 11, 2024)
        matches = find_repeated_question_pairs(first + second)

        self.assertEqual(len(first), 15)
        self.assertEqual(len(second), 15)
        self.assertEqual(len(first) * len(second), 225)
        self.assertEqual(
            {(item["question_text"], item["matching_question_text"]) for item in matches},
            {(first[1]["question_text"], second[0]["question_text"]),
             (first[4]["question_text"], second[4]["question_text"]),
             (first[8]["question_text"], second[7]["question_text"]),
             (first[10]["question_text"], second[10]["question_text"]),
             (first[12]["question_text"], second[5]["question_text"]),
             (first[14]["question_text"], second[14]["question_text"])},
        )
        self.assertTrue(all(item["match_type"] == "Similar" for item in matches))
        self.assertTrue(all(item["similarity_percentage"] >= 80.0 for item in matches))

    def test_actual_false_positive_topic_pairs_do_not_match(self):
        false_pairs = [
            ("Discuss the importance of namespaces.", "What are dynamic objects and how can you create them?"),
            ("What is the diamond problem and its solution?", "What is an exception and what is the need for exception handling?"),
            ("Discuss the requirement of operator overloading.", "Discuss the importance of namespaces and resolving conflicts."),
            ("Explain file handling using input and output streams.", "What are dynamic objects and how can you create them?"),
        ]
        for first_text, second_text in false_pairs:
            with self.subTest(first_text=first_text):
                self.assertEqual(
                    find_repeated_question_pairs([
                        question(1, 10, "oop-2023.pdf", first_text),
                        question(2, 11, "oop-2024.pdf", second_text),
                    ]),
                    [],
                )

    def test_linked_list_operations_are_not_cross_matched(self):
        operations = [
            "Insert two nodes before the first and last node of the linked list.",
            "Insert a node between the first and last node of the linked list.",
            "Insert a node at the third position in the singly linked list.",
            "Delete the first node from the singly linked list.",
            "Rearrange the linked list so even-positioned nodes come before odd-positioned nodes.",
        ]
        for index, first_text in enumerate(operations):
            for second_text in operations[index + 1:]:
                with self.subTest(first_text=first_text, second_text=second_text):
                    self.assertEqual(
                        find_repeated_question_pairs([
                            question(1, 10, "ds-2024.pdf", first_text, subject="Data Structures"),
                            question(2, 11, "ds-2025.pdf", second_text, subject="Data Structures"),
                        ]),
                        [],
                    )

    def test_genuine_linked_list_operation_paraphrases_match(self):
        rows = [
            question(1, 10, "ds-2024.pdf", "Write a function to insert a new node before the first and last nodes of a singly linked list.", subject="Data Structures"),
            question(2, 11, "ds-2025.pdf", "Implement insertion of two nodes, one ahead of the head and one before the tail in a singly linked list.", subject="Data Structures"),
        ]

        result = find_repeated_question_pairs(rows)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["match_type"], "Similar")

    def test_merge_and_print_alternate_nodes_do_not_match(self):
        rows = [
            question(1, 10, "ds-2025.pdf", "Write a C function to merge two sorted singly linked lists into a third linked list.", subject="Data Structures"),
            question(2, 11, "ds-2019.pdf", "Write a C function to print alternate nodes of a singly linked list.", subject="Data Structures"),
        ]

        self.assertEqual(find_repeated_question_pairs(rows), [])

    def test_merge_paraphrases_match(self):
        rows = [
            question(1, 10, "ds-2025.pdf", "Write a C function to merge two sorted singly linked lists into a third linked list.", subject="Data Structures"),
            question(2, 11, "ds-2024.pdf", "Implement a function that combines two sorted singly linked lists by creating a third list.", subject="Data Structures"),
        ]

        result = find_repeated_question_pairs(rows)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["match_type"], "Similar")

    def test_unclassified_linked_list_operations_do_not_match(self):
        rows = [
            question(1, 10, "ds-2025.pdf", "Describe the structure of a singly linked list and its node representation.", subject="Data Structures"),
            question(2, 11, "ds-2024.pdf", "Discuss the representation of a singly linked list and its node links.", subject="Data Structures"),
        ]

        self.assertEqual(find_repeated_question_pairs(rows), [])

    def test_indirect_component_does_not_inflate_frequency(self):
        pairs = [
            {"_first_key": (10, 1), "_second_key": (11, 1)},
            {"_first_key": (11, 1), "_second_key": (12, 1)},
        ]

        sizes = _component_sizes(pairs)

        self.assertEqual(sizes[(10, 1)], (2, 2))
        self.assertEqual(sizes[(11, 1)], (2, 2))
        self.assertEqual(sizes[(12, 1)], (2, 2))

    def test_frequency_counts_distinct_papers_for_complete_matches(self):
        rows = [
            question(1, 10, "ds-2022.pdf", "Explain inheritance and polymorphism with suitable examples."),
            question(2, 10, "ds-2022.pdf", "Explain inheritance and polymorphism with suitable examples."),
            question(3, 11, "ds-2023.pdf", "Explain inheritance and polymorphism with suitable examples."),
            question(4, 12, "ds-2024.pdf", "Explain inheritance and polymorphism with suitable examples."),
        ]

        result = find_repeated_question_pairs(rows)

        self.assertEqual(len(result), 5)
        self.assertTrue(all(item["frequency"] == 3 for item in result))
        self.assertTrue(all(item["distinct_papers"] == 3 for item in result))

    def test_unrelated_questions_do_not_match(self):
        rows = [
            question(1, 10, "oop-2024.pdf", "Explain virtual functions and dynamic dispatch in object oriented programming."),
            question(2, 11, "oop-2023.pdf", "Design a normalized relational database schema for a university registration system."),
        ]

        self.assertEqual(find_repeated_question_pairs(rows), [])

    def test_short_generic_prompts_are_ignored(self):
        rows = [
            question(1, 10, "oop-2024.pdf", "Define polymorphism."),
            question(2, 11, "oop-2023.pdf", "Define polymorphism."),
        ]

        self.assertEqual(find_repeated_question_pairs(rows), [])

    def test_pairs_are_cross_paper_and_not_duplicated(self):
        rows = [
            question(1, 10, "oop-2024.pdf", "Explain inheritance and polymorphism with suitable programming examples."),
            question(2, 10, "oop-2024.pdf", "Explain inheritance and polymorphism with suitable programming examples."),
            question(3, 11, "oop-2023.pdf", "Explain inheritance and polymorphism with suitable programming examples."),
        ]

        result = find_repeated_question_pairs(rows)

        self.assertEqual(len(result), 2)
        self.assertTrue(all(item["first_paper_id"] != item["second_paper_id"] for item in result))
        self.assertEqual(
            {(item["first_paper_id"], item["second_paper_id"]) for item in result},
            {(10, 11)},
        )


class RepeatedQuestionsEndpointTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    @patch("backend.app.list_repeated_questions")
    def test_endpoint_returns_pair_results_and_preserves_filters(self, list_repeated):
        list_repeated.return_value = [{
            "question_text": "Explain inheritance.",
            "matching_question_text": "Describe inheritance.",
            "first_paper_id": 10,
            "second_paper_id": 11,
            "similarity_percentage": 86.25,
            "match_type": "Similar",
            "frequency": 2,
            "distinct_papers": 2,
        }]
        response = self.client.get("/api/repeated-questions?subject=OOP&exam_year=2024&min_frequency=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"][0]["match_type"], "Similar")
        list_repeated.assert_called_once_with({"subject": "OOP", "exam_year": "2024", "min_frequency": "2"})

    @patch("backend.app.list_repeated_questions", side_effect=ValueError("min_frequency must be at least 2."))
    def test_invalid_minimum_frequency_is_rejected(self, _list_repeated):
        response = self.client.get("/api/repeated-questions?min_frequency=1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("at least 2", response.get_json()["error"])


class RepeatedQuestionsDatabaseTests(unittest.TestCase):
    @patch("backend.db.get_connection")
    def test_database_fetch_keeps_filters_and_delegates_to_pair_matcher(self, get_connection):
        cursor = get_connection.return_value.cursor.return_value
        cursor.fetchall.return_value = [question(
            1, 10, "oop-2023.pdf", "Explain inheritance and polymorphism with suitable programming examples.", exam_year=2023
        ), question(
            2, 11, "oop-2024.pdf", "Explain inheritance and polymorphism with suitable programming examples.", exam_year=2024
        )]

        result = list_repeated_questions({"subject": "OOP", "exam_year": "2024", "min_frequency": "2"})

        self.assertEqual(result[0]["match_type"], "Exact")
        self.assertIn(2024, result[0]["exam_years"])
        query, params = cursor.execute.call_args.args
        self.assertIn("q.normalized_hash", query)
        self.assertIn("qp.subject = %s", query)
        self.assertNotIn("qp.exam_year = %s", query)
        self.assertEqual(params, ["OOP"])


if __name__ == "__main__":
    unittest.main()
