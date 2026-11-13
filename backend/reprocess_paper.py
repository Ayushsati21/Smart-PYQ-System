"""Command-line entry point for explicitly reprocessing one paper by ID."""

from __future__ import annotations

import argparse
import sys

from .reprocess_service import PaperReprocessingError, reprocess_paper


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper_id", type=int, help="existing question_papers.id to reprocess")
    args = parser.parse_args(argv)
    try:
        result = reprocess_paper(args.paper_id)
    except PaperReprocessingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"Reprocessed paper {result['paper_id']}; "
        f"stored {result['question_count']} extracted questions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
