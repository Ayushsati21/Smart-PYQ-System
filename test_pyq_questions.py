import unittest
from pathlib import Path

from pyq_metadata import infer_metadata
from pyq_questions import extract_questions, normalize_question


class QuestionExtractionTests(unittest.TestCase):
    def test_extracts_individual_subquestions_from_tcs307_ocr(self):
        ocr_text = Path("output_text/tcs307_endsem_2023_jan.txt").read_text(encoding="utf-8")

        questions = extract_questions(ocr_text)

        self.assertEqual(len(questions), 15)
        self.assertEqual(
            [question["question_number"] for question in questions],
            [f"{main}({part})" for main in range(1, 6) for part in "abc"],
        )
        self.assertIn("Discuss the importance of namespaces", questions[1]["question_text"])
        self.assertIn("What are dynamic objects", questions[5]["question_text"])
        self.assertIn("fstream, ifstream, ofstream", questions[-1]["question_text"])

    def test_nested_roman_parts_remain_inside_parent_subquestion(self):
        questions = extract_questions(
            """1. (a) Explain this pointer.
            (i) First nested point.
            (ii) Second nested point.
            (b) Explain inheritance.
            """
        )

        self.assertEqual([question["question_number"] for question in questions], ["1(a)", "1(b)"])
        self.assertIn("(i) First nested point.", questions[0]["question_text"])
        self.assertIn("(ii) Second nested point.", questions[0]["question_text"])

    def test_numbered_only_questions_remain_compatible(self):
        questions = extract_questions("Q1) Define a stack.\n2) Define a queue.")

        self.assertEqual([question["question_number"] for question in questions], ["1", "2"])
        self.assertEqual(questions[0]["question_text"], "Define a stack.")

    def test_ocr_variations_accept_q_prefix_and_unparenthesized_submarkers(self):
        questions = extract_questions("Q 7. a) First part\n b) Second part\n7. c. Third part")

        self.assertEqual([question["question_number"] for question in questions], ["7(a)", "7(b)", "7(c)"])

    def test_uppercase_parenthesized_submarkers_are_split_sequentially(self):
        questions = extract_questions(
            "1. (A) First part\n(B) Second part\n(C) Third part"
        )

        self.assertEqual(
            [question["question_number"] for question in questions],
            ["1(a)", "1(b)", "1(c)"],
        )

    def test_uppercase_submarkers_split_2023_ocr_fixture(self):
        ocr_text = Path(
            "output_text/TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2023-11.txt"
        ).read_text(encoding="utf-8")

        questions = extract_questions(ocr_text)

        self.assertEqual(len(questions), 13)
        self.assertEqual(
            [question["question_number"] for question in questions],
            ["1(a)", "1(b)", "1(c)", "02(a)", "02(b)", "3(a)", "3(b)", "3(c)", "4(a)", "4(b)", "5(a)", "5(b)", "5(c)"],
        )
        self.assertIn("B-tree", questions[3]["question_text"])
        self.assertIn("graph traversal", questions[4]["question_text"])
        self.assertIn("delete duplicate nodes", questions[4]["question_text"])
        self.assertIn("hash collision", questions[7]["question_text"])

    def test_uppercase_submarkers_split_2024_ocr_fixture(self):
        ocr_text = Path(
            "output_text/TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2024-11.txt"
        ).read_text(encoding="utf-8")

        questions = extract_questions(ocr_text)

        self.assertEqual(len(questions), 15)
        self.assertEqual(
            [question["question_number"] for question in questions],
            ["1(a)", "1(b)", "1(c)", "2(a)", "2(b)", "2(c)", "3(a)", "3(b)", "3(c)", "4(a)", "4(b)", "4(c)", "5(a)", "5(b)", "5(c)"],
        )
        self.assertIn("B-tree", questions[3]["question_text"])
        self.assertIn("Huffman", questions[4]["question_text"])
        self.assertIn("hash collsion", questions[5]["question_text"])

    def test_malformed_submarkers_do_not_break_sequential_splitting(self):
        questions = extract_questions(
            "Q1\n(2X10=20Marks)\nA. First part\nB. Second part\nG. Malformed third part\nQ4\nA. Next question"
        )

        self.assertEqual(
            [question["question_number"] for question in questions],
            ["1(a)", "1(b)", "4(a)"],
        )
        self.assertIn("G. Malformed third part", questions[1]["question_text"])

    def test_decimal_text_is_not_a_main_question_heading(self):
        questions = extract_questions(
            "Q3.\nA. First part\n30.55,25. continuation text\nB. Second part"
        )

        self.assertEqual(
            [question["question_number"] for question in questions],
            ["3(a)", "3(b)"],
        )
        self.assertIn("30.55,25.", questions[0]["question_text"])

    def test_extracts_question_one_from_november_2025_ocr(self):
        ocr_text = Path(
            "output_text/TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2025-11.txt"
        ).read_text(encoding="utf-8")

        questions = extract_questions(ocr_text)

        self.assertEqual(
            [question["question_number"] for question in questions],
            [f"{main}({part})" for main in range(1, 6) for part in "abc"],
        )
        self.assertIn("Evaluate the following postfix expression using stack", questions[0]["question_text"])
        self.assertIn("graph trayersal techmigue", questions[1]["question_text"])
        self.assertIn("single linked list", questions[2]["question_text"])
        self.assertIn("Which algorithm would you use to compress", questions[9]["question_text"])
        self.assertIn("weighied graph", questions[10]["question_text"])
        self.assertIn("weighted graph", questions[13]["question_text"])
        self.assertIn("Write a C program", questions[12]["question_text"])
    def test_extracts_clear_numbered_blocks_and_joins_continuations(self):
        text = """--- PAGE 1 ---
Q1. What is a stack?
Explain its main operations.

2. Define a queue.
unlabelled heading
"""
        questions = extract_questions(text)
        self.assertEqual([q["question_number"] for q in questions], ["1", "2"])
        self.assertEqual(questions[0]["question_text"], "What is a stack? Explain its main operations.")
        self.assertEqual(questions[1]["question_text"], "Define a queue. unlabelled heading")

    def test_normalizes_whitespace_and_case_but_keeps_wording(self):
        self.assertEqual(
            normalize_question("  What   is a stack ? "),
            normalize_question("what is a stack?"),
        )
        self.assertNotEqual(
            normalize_question("What is a stack?"),
            normalize_question("What is a queue?"),
        )

    def test_infers_metadata_from_project_filename_pattern(self):
        metadata = infer_metadata("TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2025-11.pdf")
        self.assertEqual(metadata, {
            "subject": "Data Structures",
            "academic_year": "Second Year",
            "exam_year": 2025,
            "term": "End Term",
        })

    def test_unknown_metadata_remains_empty(self):
        self.assertEqual(infer_metadata("scan.pdf"), {
            "subject": None,
            "academic_year": None,
            "exam_year": None,
            "term": None,
        })


if __name__ == "__main__":
    unittest.main()
