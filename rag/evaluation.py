
"""Retrieval evaluation helpers."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rag.models import RetrievedDocument


class Searcher(Protocol):
    """Minimal search interface used by retrieval evaluation."""

    def search(self, query: str, *, limit: int = 3) -> list[RetrievedDocument]:
        """Return matching documents."""


@dataclass(frozen=True)
class EvaluationCase:
    """One retrieval evaluation example."""

    query: str
    expected_sources: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationResult:
    """Aggregate retrieval evaluation metrics."""

    total: int
    passed: int
    failed: int
    recall_at_k: float
    recall_at_1: float = 0.0
    mrr: float = 0.0


@dataclass(frozen=True)
class EvaluationCaseResult:
    """One retrieval evaluation case result."""

    query: str
    expected_sources: tuple[str, ...]
    returned_sources: tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class EvaluationReport:
    """Detailed retrieval evaluation report."""

    summary: EvaluationResult
    cases: tuple[EvaluationCaseResult, ...]


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    """Load retrieval evaluation cases from JSONL."""

    cases: list[EvaluationCase] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON on evaluation line {line_number}"
            ) from exc

        expected_sources = payload.get("expected_sources")

        if (
            not isinstance(payload.get("query"), str)
            or not isinstance(expected_sources, list)
        ):
            raise ValueError(f"Invalid evaluation case on line {line_number}")

        cases.append(
            EvaluationCase(
                query=payload["query"],
                expected_sources=tuple(str(source) for source in expected_sources),
            )
        )

    return cases


def evaluate_retriever(
    retriever: Searcher,
    cases: list[EvaluationCase],
    *,
    limit: int = 3,
) -> EvaluationResult:
    """Evaluate Recall@k, Recall@1, and mean reciprocal rank."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    passed = 0
    first_rank_hits = 0
    reciprocal_rank_sum = 0.0

    for case in cases:
        matches = retriever.search(case.query, limit=limit)
        expected = {
            _normalize_source_path(source)
            for source in case.expected_sources
        }

        if not expected:
            continue

        ranks = [
            rank
            for rank, match in enumerate(matches, start=1)
            if _normalize_source_path(match.document.source) in expected
        ]

        if ranks:
            passed += 1
            first_rank_hits += int(ranks[0] == 1)
            reciprocal_rank_sum += 1.0 / ranks[0]

    total = len(cases)

    return EvaluationResult(
        total=total,
        passed=passed,
        failed=total - passed,
        recall_at_k=passed / total if total else 0.0,
        recall_at_1=first_rank_hits / total if total else 0.0,
        mrr=reciprocal_rank_sum / total if total else 0.0,
    )


def evaluate_retriever_detailed(
    retriever: Searcher,
    cases: list[EvaluationCase],
    *,
    limit: int = 3,
) -> EvaluationReport:
    """Evaluate retrieval and keep per-case returned sources."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    case_results: list[EvaluationCaseResult] = []

    for case in cases:
        matches = retriever.search(case.query, limit=limit)

        returned_sources = tuple(
            _normalize_source_path(match.document.source)
            for match in matches
        )
        returned_source_set = set(returned_sources)
        expected_source_set = {
            _normalize_source_path(source)
            for source in case.expected_sources
        }

        passed = bool(expected_source_set) and expected_source_set.issubset(
            returned_source_set
        )

        case_results.append(
            EvaluationCaseResult(
                query=case.query,
                expected_sources=case.expected_sources,
                returned_sources=returned_sources,
                passed=passed,
            )
        )

    total = len(case_results)
    passed_count = sum(result.passed for result in case_results)

    # Calculate the same metrics for the detailed report.
    summary = evaluate_retriever(retriever, cases, limit=limit)

    # Use the report's actual case count and pass results.
    summary = EvaluationResult(
        total=total,
        passed=passed_count,
        failed=total - passed_count,
        recall_at_k=passed_count / total if total else 0.0,
        recall_at_1=summary.recall_at_1,
        mrr=summary.mrr,
    )

    return EvaluationReport(summary=summary, cases=tuple(case_results))


def render_markdown_report(report: EvaluationReport, *, limit: int) -> str:
    """Render a retrieval evaluation report as markdown."""

    lines = [
        "# KubePilot Retrieval Evaluation",
        "",
        f"- Recall@{limit}: {report.summary.recall_at_k:.3f}",
        f"- Recall@1: {report.summary.recall_at_1:.3f}",
        f"- MRR: {report.summary.mrr:.3f}",
        f"- Passed: {report.summary.passed}",
        f"- Failed: {report.summary.failed}",
        f"- Total: {report.summary.total}",
        "",
        "| Query | Expected Sources | Returned Sources | Result |",
        "| --- | --- | --- | --- |",
    ]

    for case_result in report.cases:
        expected = ", ".join(case_result.expected_sources) or "-"
        returned = ", ".join(case_result.returned_sources) or "-"
        result = "pass" if case_result.passed else "fail"

        lines.append(
            f"| {_escape_table_cell(case_result.query)} | "
            f"{_escape_table_cell(expected)} | "
            f"{_escape_table_cell(returned)} | {result} |"
        )

    return "\n".join(lines) + "\n"


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _normalize_source_path(source: str) -> str:
    """Normalize source paths for cross-platform comparison."""

    return source.replace("\\", "/")
