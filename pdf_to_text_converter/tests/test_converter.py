import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf as fitz

from batch_pdf_to_text import convert_directory
from pdf_to_text import ScannedPDFError, convert_pdf


class FakeResult:
    json = {"res": {"rec_texts": ["Recognized sample text", "  "]}}


class FakeOCR:
    def predict(self, image_path):
        self.last_image = Path(image_path)
        return [FakeResult()]


def make_pdf(path, text="Synthetic permitted sample"):
    document = fitz.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


class ConverterTests(unittest.TestCase):
    def test_extracts_embedded_text_without_initializing_ocr(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "searchable.pdf"
            destination = root / "nested" / "searchable.txt"
            make_pdf(source, "This is a searchable question paper with enough text.")

            with patch("pdf_to_text.create_ocr", side_effect=AssertionError("OCR must not load")):
                text, page_count = convert_pdf(source, destination)

            self.assertEqual(page_count, 1)
            self.assertIn("searchable question paper", text)
            self.assertTrue(destination.is_file())

    def test_scanned_pdf_is_rejected_without_ocr(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "scanned.pdf"
            make_pdf(source, "")
            with self.assertRaises(ScannedPDFError):
                convert_pdf(source, root / "scanned.txt")
            self.assertFalse((root / "scanned.txt").exists())

    def test_explicit_ocr_path_still_works(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "sample.pdf"
            destination = root / "new" / "nested" / "sample.txt"
            make_pdf(source)

            text, page_count = convert_pdf(source, destination, ocr=FakeOCR())

            self.assertEqual(page_count, 1)
            self.assertEqual(text, "--- PAGE 1 ---\nRecognized sample text")
            self.assertEqual(destination.read_text(encoding="utf-8"), text)

    def test_missing_and_invalid_pdfs_fail_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing_output = root / "missing.txt"
            with self.assertRaises(FileNotFoundError):
                convert_pdf(root / "missing.pdf", missing_output)
            self.assertFalse(missing_output.exists())

            invalid_pdf = root / "invalid.pdf"
            invalid_pdf.write_bytes(b"not a PDF")
            with self.assertRaises(Exception):
                convert_pdf(invalid_pdf, root / "invalid.txt")
            self.assertFalse((root / "invalid.txt").exists())

    def test_batch_converts_multiple_pdfs_and_preserves_subdirectories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = root / "inputs"
            outputs = root / "outputs"
            (inputs / "nested").mkdir(parents=True)
            make_pdf(inputs / "one.pdf")
            make_pdf(inputs / "nested" / "two.pdf")

            with patch("batch_pdf_to_text.create_ocr", return_value=FakeOCR()):
                succeeded, failed = convert_directory(inputs, outputs)

            self.assertEqual((succeeded, failed), (2, 0))
            self.assertTrue((outputs / "one.txt").is_file())
            self.assertTrue((outputs / "nested" / "two.txt").is_file())

    def test_empty_input_directory_does_not_initialize_ocr(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = root / "inputs"
            inputs.mkdir()
            with patch("batch_pdf_to_text.create_ocr") as create_ocr:
                self.assertEqual(convert_directory(inputs, root / "outputs"), (0, 0))
                create_ocr.assert_not_called()


if __name__ == "__main__":
    unittest.main()
