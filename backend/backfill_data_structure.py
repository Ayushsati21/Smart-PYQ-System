"""Allowlisted dry-run and repair entry point for the four legacy DS papers.

The default operation is a read-only dry-run. Database repair requires the
explicit ``--execute`` flag and delegates stored-OCR processing to
``backend.reprocess_service.reprocess_paper``.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .reprocess_service import _deduplicate_questions, reprocess_paper


BASE_DIR = Path(__file__).resolve().parents[1]
TARGET_PAPERS = {
    2: "TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2023-11.txt",
    3: "TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2024-11.txt",
    4: "TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2025-11.txt",
    5: "TCS302_DataStructures_CSE_Sem3_MidTerm_Odd_2019.txt",
}


@dataclass(frozen=True)
class BackfillPlan:
    paper_id: int
    text_path: Path
    questions: tuple[dict, ...]

    @property
    def insertion_count(self) -> int:
        return len(self.questions)


def validate_paper_ids(paper_ids: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    """Require exactly the four approved paper IDs, in caller-provided order."""

    ids = tuple(paper_ids)
    if set(ids) != set(TARGET_PAPERS) or len(ids) != len(TARGET_PAPERS):
        expected = ", ".join(str(paper_id) for paper_id in TARGET_PAPERS)
        raise ValueError(f"Only paper IDs {expected} are permitted.")
    return ids


def build_plans(
    base_dir: Path = BASE_DIR,
    paper_ids: list[int] | tuple[int, ...] = tuple(TARGET_PAPERS),
) -> tuple[BackfillPlan, ...]:
    """Read and parse only the existing OCR files; never touches the database."""

    from pyq_questions import extract_questions

    ids = validate_paper_ids(list(paper_ids))
    plans: list[BackfillPlan] = []
    for paper_id in ids:
        text_path = base_dir / "output_text" / TARGET_PAPERS[paper_id]
        if not text_path.is_file():
            raise FileNotFoundError(f"Stored OCR text is missing: {text_path}")
        text = text_path.read_text(encoding="utf-8")
        questions = tuple(_deduplicate_questions(extract_questions(text)))
        plans.append(BackfillPlan(paper_id, text_path, questions))
    return tuple(plans)


def format_dry_run(plans: tuple[BackfillPlan, ...]) -> str:
    """Return a human-readable, exact question-level dry-run report."""

    lines = ["DRY RUN ONLY: no database statements were executed."]
    total = 0
    for plan in plans:
        lines.append(f"Paper ID {plan.paper_id}: {plan.text_path}")
        lines.append(f"  Expected insertions: {plan.insertion_count}")
        for question in plan.questions:
            lines.append(
                f"  {question['question_number']}: {question['question_text']}"
            )
        total += plan.insertion_count
    lines.append(f"Expected total insertions: {total}")
    return "\n".join(lines)


def execute_repair(
    plans: tuple[BackfillPlan, ...],
    reprocess: Callable[[int], dict[str, int]] = reprocess_paper,
) -> tuple[dict[str, int], ...]:
    """Repair only the planned IDs using the existing transactional service."""

    results: list[dict[str, int]] = []
    for plan in plans:
        result = reprocess(plan.paper_id)
        actual = int(result["question_count"])
        if actual != plan.insertion_count:
            raise RuntimeError(
                f"Paper {plan.paper_id}: expected {plan.insertion_count} questions, "
                f"but the repair reported {actual}."
            )
        results.append(result)
    return tuple(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-ids", nargs="+", type=int, default=list(TARGET_PAPERS))
    parser.add_argument("--dry-run", action="store_true", help="read and report only")
    parser.add_argument("--execute", action="store_true", help="perform the database repair")
    args = parser.parse_args(argv)
    if args.dry_run == args.execute:
        parser.error("choose exactly one of --dry-run or --execute")

    try:
        plans = build_plans(paper_ids=args.paper_ids)
        if args.dry_run:
            print(format_dry_run(plans))
            return 0
        for result in execute_repair(plans):
            print(
                f"Repaired paper {result['paper_id']}; "
                f"stored {result['question_count']} extracted questions."
            )
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
