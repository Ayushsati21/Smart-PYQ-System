"""OCR text from every page of a PDF using PyMuPDF and PaddleOCR."""

import argparse
import json
import tempfile
from pathlib import Path

import pymupdf as fitz
from paddleocr import PaddleOCR


MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = MODULE_DIR / "input_pdfs"
DEFAULT_OUTPUT_DIR = MODULE_DIR / "output_text"


def extract_text(results):
    """Return recognized text lines from PaddleOCR's prediction results."""
    lines = []
    for result in results:
        data = getattr(result, "json", None)
        if callable(data):
            data = data()
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict):
            continue
        data = data.get("res", data)
        if not isinstance(data, dict):
            continue
        for text in data.get("rec_texts", []):
            if text and str(text).strip():
                lines.append(str(text).strip())
    return lines


def create_ocr():
    """Initialize the CPU OCR engine."""
    return PaddleOCR(
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
        device="cpu",
        enable_mkldnn=True,
        cpu_threads=4,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_det_limit_side_len=1600,
        text_det_limit_type="max",
    )


def convert_pdf(pdf_path, output_path, ocr=None):
    """OCR a PDF and save page-marked UTF-8 text; return (text, page_count)."""
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    engine = ocr if ocr is not None else create_ocr()
    page_texts = []
    with tempfile.TemporaryDirectory(prefix="pyq_ocr_") as temp_dir:
        with fitz.open(pdf_path) as pdf:
            if len(pdf) == 0:
                raise ValueError(f"PDF contains no pages: {pdf_path}")
            for page_number, page in enumerate(pdf, start=1):
                image_path = Path(temp_dir) / f"page_{page_number}.png"
                page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False).save(str(image_path))
                page_text = "\n".join(extract_text(engine.predict(str(image_path))))
                page_texts.append(f"--- PAGE {page_number} ---\n{page_text}")

    text = "\n\n".join(page_texts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    return text, len(page_texts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="PDF file to OCR")
    parser.add_argument("output", type=Path, help="Destination text file")
    args = parser.parse_args()
    text, pages = convert_pdf(args.pdf, args.output)
    print(f"Processed {pages} page(s); recognized {len(text)} characters.")
    print(f"Output saved to: {args.output}")


if __name__ == "__main__":
    main()
