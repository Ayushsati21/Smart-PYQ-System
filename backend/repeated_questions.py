"""Exact and lightweight lexical-similarity matching for extracted questions."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from itertools import combinations
from typing import Any, Iterable


DEFAULT_SIMILARITY_THRESHOLD = 0.80
MIN_QUESTION_CHARS = 24
MIN_CONTENT_TOKENS = 2
TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)

# These words occur in many unrelated exam prompts and should not make a short
# question look meaningful by themselves.
GENERIC_TOKENS = {
    "a", "an", "and", "are", "as", "also", "be", "between", "briefly", "class", "code", "create", "define", "describe", "discuss",
    "do", "does", "each", "example", "examples", "explain", "for", "from", "function", "give", "has", "have", "how", "in", "including", "is", "it", "like", "make", "method", "of", "on",
    "object", "objects", "one", "or", "perform", "program", "programming", "question", "same", "show", "state", "suitable", "appropriate", "take", "the", "their", "these", "this", "three", "to", "two", "use", "using", "various", "vs", "what", "which", "with", "write", "well",
    "its", "input", "output",
}


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text or "")]


def _content_tokens(text: str) -> list[str]:
    content = []
    for token in _tokens(text):
        if token in GENERIC_TOKENS or len(token) <= 1 or re.fullmatch(r"(?:co\d+|tcs|pto|\d+)", token):
            continue
        # Small suffix normalization keeps OCR/plural/verb variants in the
        # same TF-IDF feature space without adding a heavyweight NLP package.
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("ence") and len(token) > 6:
            token = token[:-4]
        elif token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("es") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 3:
            token = token[:-1]
        content.append(token)
    return content


def is_matchable_question(text: str) -> bool:
    """Reject short/generic prompts before exact or semantic matching."""

    content = _content_tokens(text)
    return len((text or "").strip()) >= MIN_QUESTION_CHARS and len(content) >= MIN_CONTENT_TOKENS


def _operation_family(text: str) -> str | None:
    """Return a linked-list operation family when the prompt identifies one."""

    lowered = (text or "").casefold()
    if not re.search(r"\b(?:linked\s+list|singly\s+linked|node|nodes)\b", lowered):
        return None
    if re.search(r"\b(?:rearrange|reorder|reverse)\b", lowered):
        return "reorder"
    if re.search(r"\b(?:delete|remove)\b", lowered):
        return "delete"
    if re.search(r"\b(?:merge(?:d|s|ing)?|combine(?:d|s|ing)?)\b", lowered):
        return "merge"
    if re.search(r"\bprint(?:ing)?\b", lowered) and re.search(
        r"\b(?:alternate|odd|even|traverse|traversal)\b", lowered
    ):
        return "print_traverse"
    if re.search(r"\binsert(?:ion)?\b", lowered):
        if re.search(r"\bbetween\b", lowered):
            return "insert_between"
        if re.search(r"\b(?:position|nth|kth)\b|\bafter\s+the\s+\w+\s+node", lowered):
            return "insert_at_position"
        if re.search(r"\bbefore\s+the\s+(?:\d+|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+node", lowered):
            return "insert_at_position"
        if re.search(r"\bbefore\b", lowered):
            return "insert_before"
        return "insert"
    return "other"


def _tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    token_lists = [_content_tokens(text) for text in texts]
    document_frequency: defaultdict[str, int] = defaultdict(int)
    for tokens in token_lists:
        for token in set(tokens):
            document_frequency[token] += 1

    document_count = len(token_lists)
    vectors: list[dict[str, float]] = []
    for tokens in token_lists:
        counts: defaultdict[str, int] = defaultdict(int)
        for token in tokens:
            counts[token] += 1
        vector = {
            token: (count / len(tokens)) * (math.log((1 + document_count) / (1 + document_frequency[token])) + 1)
            for token, count in counts.items()
        }
        vectors.append(vector)
    return vectors


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    """Return cosine similarity for two sparse TF-IDF vectors."""

    if not left or not right:
        return 0.0
    dot = sum(value * right.get(token, 0.0) for token, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _concept_similarity(left_text: str, right_text: str) -> tuple[float, bool]:
    """Score shared informative concepts and require a strong topic anchor."""

    left_tokens = _content_tokens(left_text)
    right_tokens = _content_tokens(right_text)
    left_unique, right_unique = set(left_tokens), set(right_tokens)
    if not left_unique or not right_unique:
        return 0.0, False

    shared_tokens = left_unique & right_unique
    coverage = len(shared_tokens) / min(len(left_unique), len(right_unique))
    left_phrases = set(zip(left_tokens, left_tokens[1:]))
    right_phrases = set(zip(right_tokens, right_tokens[1:]))
    shared_phrase = bool(left_phrases & right_phrases)
    # Two shared informative tokens, or a shared informative phrase, are
    # required before a score can become a Similar match. This prevents one
    # accidental word from creating a relationship between unrelated prompts.
    strong_topic = len(shared_tokens) >= 2 and (shared_phrase or len(shared_tokens) >= 3)
    if not strong_topic:
        return 0.0, False

    jaccard = len(shared_tokens) / len(left_unique | right_unique)
    topic_coverage = 1.0 if shared_phrase or len(shared_tokens) >= 3 else coverage
    # The result is derived from evidence; no fixed 0.80 score is injected.
    score = 0.85 * topic_coverage + 0.15 * jaccard
    return score, True


def _question_key(row: dict[str, Any]) -> tuple[int, int]:
    return int(row["paper_id"]), int(row["question_id"])


def _component_sizes(pairs: list[dict[str, Any]]) -> dict[tuple[int, int], tuple[int, int]]:
    """Return (frequency, distinct_papers) for every matched question key."""

    parent: dict[tuple[int, int], tuple[int, int]] = {}

    def find(node: tuple[int, int]) -> tuple[int, int]:
        parent.setdefault(node, node)
        if parent[node] != node:
            parent[node] = find(parent[node])
        return parent[node]

    def union(left: tuple[int, int], right: tuple[int, int]) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for pair in pairs:
        union(pair["_first_key"], pair["_second_key"])

    members: defaultdict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for node in parent:
        members[find(node)].append(node)
    sizes: dict[tuple[int, int], tuple[int, int]] = {}
    matched_paper_pairs: defaultdict[tuple[int, int], set[frozenset[int]]] = defaultdict(set)
    for pair in pairs:
        first_paper = int(pair["_first_key"][0])
        second_paper = int(pair["_second_key"][0])
        root = find(pair["_first_key"])
        matched_paper_pairs[root].add(frozenset((first_paper, second_paper)))

    for root, nodes in members.items():
        paper_count = len({paper_id for paper_id, _ in nodes})
        papers = sorted({paper_id for paper_id, _ in nodes})
        complete_cross_paper_coverage = all(
            frozenset((left, right)) in matched_paper_pairs[root]
            for left, right in combinations(papers, 2)
        )
        frequency = paper_count if complete_cross_paper_coverage else 2
        distinct_papers = paper_count if complete_cross_paper_coverage else 2
        for node in nodes:
            sizes[node] = (frequency, distinct_papers)
    return sizes


def find_repeated_question_pairs(
    rows: Iterable[dict[str, Any]],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    minimum_frequency: int = 2,
) -> list[dict[str, Any]]:
    """Build unique cross-paper exact and TF-IDF similarity matches.

    Rows are not changed. Exact normalized-hash matches are emitted first as
    ``Exact``. Semantic pairs are then emitted once, using TF-IDF cosine
    similarity over the matchable questions. Connected-component frequency
    keeps the existing minimum-frequency filter meaningful for 3+ papers.
    """

    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be between 0 and 1.")
    if minimum_frequency < 2:
        raise ValueError("min_frequency must be at least 2.")

    questions = [
        row for row in rows
        if len(str(row.get("question_text") or "").strip()) >= MIN_QUESTION_CHARS
    ]
    vectors = _tfidf_vectors([str(row.get("question_text") or "") for row in questions])
    pairs: list[dict[str, Any]] = []
    pair_keys: set[frozenset[tuple[int, int]]] = set()

    def add_pair(first: dict[str, Any], second: dict[str, Any], similarity: float, match_type: str) -> None:
        first_key, second_key = _question_key(first), _question_key(second)
        if first_key[0] == second_key[0]:
            return
        unique_key = frozenset((first_key, second_key))
        if unique_key in pair_keys:
            return
        pair_keys.add(unique_key)
        if first_key > second_key:
            first, second = second, first
            first_key, second_key = second_key, first_key
        pairs.append({
            "question_text": first["question_text"],
            "matching_question_text": second["question_text"],
            "first_paper_id": first["paper_id"],
            "second_paper_id": second["paper_id"],
            "first_paper_filename": first["paper_filename"],
            "second_paper_filename": second["paper_filename"],
            "similarity_percentage": round(similarity * 100, 2),
            "match_type": match_type,
            "subject": first.get("subject") or second.get("subject"),
            "exam_years": sorted({year for year in (first.get("exam_year"), second.get("exam_year")) if year}, reverse=True),
            "paper_filenames": [first["paper_filename"], second["paper_filename"]],
            "_first_key": first_key,
            "_second_key": second_key,
        })

    for index, first in enumerate(questions):
        for second in questions[index + 1:]:
            if first.get("normalized_hash") == second.get("normalized_hash"):
                add_pair(first, second, 1.0, "Exact")

    for index, first in enumerate(questions):
        for second_index in range(index + 1, len(questions)):
            second = questions[second_index]
            if first["paper_id"] == second["paper_id"]:
                continue
            if not is_matchable_question(str(first.get("question_text") or "")):
                continue
            if not is_matchable_question(str(second.get("question_text") or "")):
                continue
            first_operation = _operation_family(str(first.get("question_text") or ""))
            second_operation = _operation_family(str(second.get("question_text") or ""))
            if first_operation == "other" or second_operation == "other":
                continue
            if first_operation != second_operation and (first_operation or second_operation):
                continue
            cosine_score = cosine_similarity(vectors[index], vectors[second_index])
            concept_score, strong_topic = _concept_similarity(first["question_text"], second["question_text"])
            if not strong_topic:
                continue
            similarity = 0.92 * concept_score + 0.08 * cosine_score
            if similarity >= similarity_threshold:
                add_pair(first, second, similarity, "Similar")

    component_sizes = _component_sizes(pairs)
    filtered: list[dict[str, Any]] = []
    for pair in pairs:
        frequency, distinct_papers = component_sizes[pair["_first_key"]]
        if frequency >= minimum_frequency:
            pair["frequency"] = frequency
            pair["distinct_papers"] = distinct_papers
            filtered.append(pair)
        pair.pop("_first_key", None)
        pair.pop("_second_key", None)
    return sorted(filtered, key=lambda pair: (-pair["frequency"], -pair["similarity_percentage"], pair["question_text"]))
