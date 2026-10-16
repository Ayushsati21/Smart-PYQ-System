# PDF-to-Text Converter

This module converts PDF pages to UTF-8 text with OCR. PyMuPDF renders each page to an image and PaddleOCR recognizes its text. Text-based and scanned PDFs both use this OCR workflow; embedded PDF text is not extracted directly.

## Workflow

Put permitted PDFs in `input_pdfs/`. Run the batch command to create matching `.txt` files under `output_text/`; nested input folders are mirrored. Each output includes `--- PAGE N ---` markers. The single-file command accepts explicit input and output paths.

## Installation

Use Python 3.10 or newer in a virtual environment, then install the listed packages:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

PaddleOCR downloads its configured PP-OCRv5 mobile models on first use. Model download requires network access. The converter runs OCR on CPU.

## Usage

From this directory, convert every PDF under `input_pdfs/`:

```powershell
python batch_pdf_to_text.py
```

Choose alternate directories with `--input-dir` and `--output-dir`:

```powershell
python batch_pdf_to_text.py --input-dir .\input_pdfs --output-dir .\output_text
```

Convert one PDF:

```powershell
python pdf_to_text.py .\input_pdfs\paper.pdf .\output_text\paper.txt
```

## Dependencies

`requirements.txt` contains PyMuPDF for PDF rendering, PaddleOCR for recognition, and PaddlePaddle as its inference runtime.

## Limitations

- Pages are rasterized and OCR can misread text, especially low-resolution, rotated, handwritten, or complex layouts.
- This module does not extract a PDF's embedded text layer or perform question parsing, metadata inference, database updates, or frequency analysis.
- A valid PDF with no recognized text produces page markers and empty page text; review the output when OCR quality matters.
- Do not commit personal, confidential, or copyrighted PDFs unless you have permission. Input PDFs and generated output files are ignored by Git.
