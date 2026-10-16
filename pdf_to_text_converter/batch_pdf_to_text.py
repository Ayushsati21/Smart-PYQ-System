"""Convert all PDFs under input_pdfs to page-marked text files."""

import argparse
from pathlib import Path

from pdf_to_text import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, convert_pdf, create_ocr


def convert_directory(input_dir=DEFAULT_INPUT_DIR, output_dir=DEFAULT_OUTPUT_DIR):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_dir}")

    pdf_paths = sorted(
        (path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf"),
        key=lambda path: path.relative_to(input_dir).as_posix().casefold(),
    )
    if not pdf_paths:
        print(f"No PDF files found under {input_dir}")
        return 0, 0

    output_dir.mkdir(parents=True, exist_ok=True)
    ocr = None
    succeeded = 0
    failed = 0
    for pdf_path in pdf_paths:
        relative_pdf = pdf_path.relative_to(input_dir)
        output_path = (output_dir / relative_pdf).with_suffix(".txt")
        try:
            if ocr is None:
                ocr = create_ocr()
            text, pages = convert_pdf(pdf_path, output_path, ocr=ocr)
            print(f"SAVED {output_path} ({pages} page(s), {len(text)} characters)")
            succeeded += 1
        except Exception as exc:
            print(f"FAILED {relative_pdf}: {exc}")
            failed += 1
    return succeeded, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    succeeded, failed = convert_directory(args.input_dir, args.output_dir)
    print(f"\nCompleted: {succeeded} succeeded, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
