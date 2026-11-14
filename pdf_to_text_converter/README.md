# PDF-to-Text Converter

This module extracts embedded PDF text with PyMuPDF by default. PaddleOCR is optional and is used only when explicitly requested for scanned PDFs. The hosted Flask upload service uses the lightweight embedded-text path so it can run on a small memory instance.

## Hosted upload behavior

- Searchable/text-based PDFs are uploaded and processed on Render using PyMuPDF.
- Scanned PDFs without a usable embedded text layer are rejected with a clear message instead of loading PaddleOCR and exhausting the hosted worker's memory.
- To process a scanned PDF, run the local OCR workflow below, then create/upload a searchable PDF or otherwise add a text layer before using the hosted upload form.

## Local installation

Use Python 3.10 or newer in a virtual environment, then install the listed packages:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

PaddleOCR downloads its configured PP-OCRv5 mobile models on first use. Model download requires network access. OCR runs on CPU.

## Usage

From this directory, convert every PDF under `input_pdfs/` with local OCR:

```powershell
python batch_pdf_to_text.py
```

Choose alternate directories with `--input-dir` and `--output-dir`:

```powershell
python batch_pdf_to_text.py --input-dir .\input_pdfs --output-dir .\output_text
```

Extract embedded text from one PDF without OCR:

```powershell
python pdf_to_text.py .\input_pdfs\paper.pdf .\output_text\paper.txt
```

Use PaddleOCR locally for a scanned PDF:

```powershell
python pdf_to_text.py .\input_pdfs\paper.pdf .\output_text\paper.txt --ocr
```

## Dependencies

The local `requirements.txt` contains PyMuPDF, PaddleOCR, and PaddlePaddle. Render installs only backend requirements plus PyMuPDF; PaddleOCR is deliberately excluded from the hosted worker.

## Limitations

- Embedded-text extraction cannot read image-only/scanned pages; use the local OCR workflow for those.
- OCR can misread low-resolution, rotated, handwritten, or complex layouts.
- This module does not perform question parsing, metadata inference, database updates, or frequency analysis.
- Do not commit personal, confidential, or copyrighted PDFs unless you have permission. Input PDFs and generated output files are ignored by Git.
