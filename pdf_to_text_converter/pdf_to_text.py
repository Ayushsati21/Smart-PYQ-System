"""Extract text from PDFs cheaply, with optional local PaddleOCR for scanned files."""

import argparse
import json
import tempfile
from pathlib import Path

import pymupdf as fitz


MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = MODULE_DIR / "input_pdfs"
DEFAULT_OUTPUT_DIR = MODULE_DIR / "output_text"


class ScannedPDFError(ValueError):
    """Raised when a PDF has no usable embedded text layer."""


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
    """Initialize PaddleOCR on demand; importing this module stays lightweight."""
    from paddleocr import PaddleOCR

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



def pdf_has_images(pdf_path):
    """Return True when any page contains a raster image (common in scanned papers)."""
    with fitz.open(pdf_path) as pdf:
        return any(page.get_images(full=True) for page in pdf)


def extract_with_tesseract(pdf_path, dpi_scale=1.5, page_timeout=45):
    """OCR image-based pages with bounded CPU and memory use for small hosts."""
    try:
        import pytesseract
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR dependencies are unavailable. Install pytesseract, Pillow, "
            "and the tesseract-ocr system package."
        ) from exc

    page_texts = []
    with fitz.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(dpi_scale, dpi_scale),
                colorspace=fitz.csRGB,
                alpha=False,
            )
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            page_text = pytesseract.image_to_string(
                image, config="--psm 6", timeout=page_timeout
            ).strip()
            page_texts.append(f"--- PAGE {page_number} ---\n{page_text}")
    return "\n\n".join(page_texts), len(page_texts)


def convert_pdf(pdf_path, output_path, ocr=None):
    """Write page-marked text. Use embedded text by default; OCR only when supplied.

    The hosted upload service may compare this lightweight extraction with
    Tesseract OCR for image-based PDFs.
    """
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    page_texts = []
    with tempfile.TemporaryDirectory(prefix="pyq_ocr_") as temp_dir:
        with fitz.open(pdf_path) as pdf:
            if len(pdf) == 0:
                raise ValueError(f"PDF contains no pages: {pdf_path}")
            for page_number, page in enumerate(pdf, start=1):
                if ocr is None:
                    page_text = page.get_text("text", sort=True).strip()
                else:
                    image_path = Path(temp_dir) / f"page_{page_number}.png"
                    page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False).save(str(image_path))
                    page_text = "\n".join(extract_text(ocr.predict(str(image_path))))
                page_texts.append(f"--- PAGE {page_number} ---\n{page_text}")

    text = "\n\n".join(page_texts)
    if ocr is None:
        embedded_characters = sum(
            len(page_text.split("\n", 1)[1].strip()) for page_text in page_texts
        )
        if embedded_characters < 20:
            raise ScannedPDFError(
                "This PDF appears to be scanned and has no usable embedded text. "
                "Run the local PaddleOCR converter on this PDF, then upload a text-based/searchable PDF."
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    return text, len(page_texts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="PDF file to OCR or extract")
    parser.add_argument("output", type=Path, help="Destination text file")
    parser.add_argument("--ocr", action="store_true", help="Use PaddleOCR for scanned PDFs (local use)")
    args = parser.parse_args()
    engine = create_ocr() if args.ocr else None
    text, pages = convert_pdf(args.pdf, args.output, ocr=engine)
    print(f"Processed {pages} page(s); recognized {len(text)} characters.")
    print(f"Output saved to: {args.output}")


if __name__ == "__main__":
    main()
