import unittest

from pyq_questions import extract_questions


class OCRQuestionExtractionTests(unittest.TestCase):
    def test_splits_inline_numbered_subquestion_markers(self):
        ocr_text = """Question text before marker 3(a) Delete a node from a singly linked list.
More text for part a. 3(b) Insert a node before the last node.
"""
        questions = extract_questions(ocr_text)
        self.assertEqual(
            [question["question_number"] for question in questions],
            ["3(a)", "3(b)"],
        )
        self.assertIn("Delete a node", questions[0]["question_text"])
        self.assertIn("Insert a node", questions[1]["question_text"])

    def test_recovers_all_ten_alternatives_from_common_ocr_noise(self):
        ocr_text = """--- PAGE 1 ---
Qu. (10*1,C01,C02)
A.Assume that you have a stack implemented with linked list.
OR .
B.Explain dynamic array and print the third non-repeating element.
Q2. (10*1,C01,C03)
A. Consider a circular linked list and insert a node.
OR
. B, Evaluate the following postfix expression using stack.
Q3.
A. Delete a node from a singly linked list.
OR
B. Insert a node before the last node in a doubly linked list.
--- PAGE 2 ---
Q4.
A. Print the node having highest information in a singly linked list.
OR
B. Print the addition of data in two linked lists.
Q5.
A. Count nodes having information multiple of 3.
OR
B. Print alternate nodes in a linked list.
"""
        questions = extract_questions(ocr_text)
        self.assertEqual(len(questions), 10)
        self.assertEqual(
            [question["question_number"] for question in questions],
            [
                "1(a)", "1(b)", "2(a)", "2(b)", "3(a)",
                "3(b)", "4(a)", "4(b)", "5(a)", "5(b)",
            ],
        )
        self.assertTrue(all(question["question_text"] for question in questions))
        self.assertTrue(all(" or " not in question["question_text"].casefold() for question in questions))


if __name__ == "__main__":
    unittest.main()
