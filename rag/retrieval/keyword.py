
"""Keyword-based retriever with phrase and intent-aware ranking."""

import re
from collections import Counter
from pathlib import Path

from rag.chunking import chunk_markdown
from rag.loaders import load_markdown_documents
from rag.models import Document, RetrievedDocument

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

IMPORTANT_TERMS = {
    "crashloopbackoff",
    "imagepullbackoff",
    "oomkilled",
    "readiness",
    "liveness",
    "pending",
    "scheduling",
    "rollout",
    "restart",
    "probe",
    "cpu",
    "memory",
    "registry",
}


class KeywordRetriever:
    """Rank documents using keyword overlap and query intent."""

    def __init__(self, documents: list[Document]) -> None:
        self._documents = documents

    def search(
        self,
        query: str,
        *,
        limit: int = 3,
    ) -> list[RetrievedDocument]:
        """Return the most relevant unique runbooks for a query."""

        if limit < 1:
            return []

        query_terms = _token_counts(query)
        if not query_terms:
            return []

        matches: list[RetrievedDocument] = []

        for document in self._documents:
            score = _score_document(query_terms, document)


            if score > 0:
                matches.append(
                    RetrievedDocument(document=document, score=score)
                )

        matches.sort(
            key=lambda match: (
                -match.score,
                match.document.title,
                match.document.source,
            )
        )

        unique_matches: list[RetrievedDocument] = []
        seen_sources: set[str] = set()

        for match in matches:
            source = match.document.source

            if source in seen_sources:
                continue

            seen_sources.add(source)
            unique_matches.append(match)

            if len(unique_matches) >= limit:
                break

        return unique_matches


def create_default_retriever(
    runbooks_dir: Path | None = None,
) -> KeywordRetriever:
    """Create a keyword retriever over the local runbook directory."""

    directory = runbooks_dir or Path("docs/runbooks")
    documents = chunk_markdown(load_markdown_documents(directory))
    return KeywordRetriever(documents)


def _score_document(
    query_terms: Counter[str],
    document: Document,
) -> int:
    title_terms = _token_counts(document.title)
    content_terms = _token_counts(document.content)

    title_score = sum(
        count * title_terms.get(term, 0)
        for term, count in query_terms.items()
    )
    content_score = sum(
        count * content_terms.get(term, 0)
        for term, count in query_terms.items()
    )

    specific_score = sum(
        count
        for term, count in query_terms.items()
        if term in IMPORTANT_TERMS
        and (
            title_terms.get(term, 0) > 0
            or content_terms.get(term, 0) > 0
        )
    )

    score = title_score * 5 + content_score + specific_score * 3

    query = set(query_terms)
    title = set(title_terms)
    content = set(content_terms)
    document_terms = title | content

    # Prefer the dedicated rolling-restart runbook for safe,
    # gradual, or downtime-conscious restart requests.
    restart_intent = bool(
        query & {"restart", "deployment", "pod", "rollout"}
    )
    safe_restart_intent = bool(
        query & {"safely", "gradually", "downtime", "rolling", "without"}
    )

    if restart_intent and safe_restart_intent:
        if {"rolling", "restart"} <= title:
            score += 80

     # Prefer the unhealthy-workloads runbook for general workload health.
    unhealthy_intent = bool(
        query & {"unhealthy", "workload", "replica", "failed"}
    )
    specific_rollout_intent = bool(
        query & {"rollout", "available"}
    )

    if unhealthy_intent and not specific_rollout_intent:
        if {"unhealthy", "workload"} <= title:
            score += 40



    # Prefer the dependency runbook for database connectivity,
    # connection errors, DNS, and dependency hostname problems.
    dependency_intent = bool(
        query
        & {
            "database",
            "connection",
            "connect",
            "timeout",
            "hostname",
            "dependency",
            "dns",
            "credentials",
        }
    )

    if dependency_intent:
        if {"dependency", "connection"} <= title:
            score += 25
        elif "database" in query and "database" in document_terms:
            score += 8


    # Strongly prefer the runbook matching the operator's specific issue.
    intents = [
        (
    {
        "imagepullbackoff",
        "errimagepull",
        "image",
        "pull",
        "registry",
        "authentication",
        "auth",
        "credential",
        "private",
    },
    {"image", "pull", "backoff"},
),
        ({"pending", "unschedulable", "scheduling"},
         {"pending", "pods", "scheduling"}),
        ({"rollout", "deployment", "deploy"},
         {"deployment", "rollout", "failures"}),
        ({"readiness", "probe", "liveness"},
         {"readiness", "probe", "failures"}),
        ({"crashloopbackoff", "oomkilled"},
         {"pod", "restarts"}),
        ({"dependency", "connection", "dns", "timeout", "database"},
         {"dependency", "connection", "failures"}),
        ({"unhealthy", "workload"},
         {"unhealthy", "workloads"}),
    ]

    for query_markers, title_markers in intents:
        if query & query_markers and title_markers <= title:
            score += 50

    # Reward matching multiword phrases when they appear in the title.
    query_tokens = _tokenize(query_terms)
    title_tokens = _tokenize(_token_counts(document.title))

    if len(query_tokens) >= 2:
        for size in (3, 2):
            if len(query_tokens) < size:
                continue

            query_phrases = {
                tuple(query_tokens[i : i + size])
                for i in range(len(query_tokens) - size + 1)
            }
            title_phrases = {
                tuple(title_tokens[i : i + size])
                for i in range(len(title_tokens) - size + 1)
            }
            score += 3 * len(query_phrases & title_phrases)

    return score


def _tokenize(term_counts: Counter[str]) -> list[str]:
    """Expand normalized token counts into a deterministic token list."""

    return [
        term
        for term, count in term_counts.items()
        for _ in range(count)
    ]


def _token_counts(text: str) -> Counter[str]:
    tokens = TOKEN_PATTERN.findall(text.lower())
    return Counter(_normalize_token(token) for token in tokens)


def _normalize_token(token: str) -> str:
    """Normalize common English variants and Kubernetes terminology."""

    synonyms = {
        # Restart and crash terminology
        "crashing": "restart",
        "crash": "restart",
        "crashes": "restart",
        "crashed": "restart",
        "restarting": "restart",
        "restarts": "restart",
        "restarted": "restart",
        "dying": "restart",
        "terminate": "restart",
        "terminated": "restart",
        "terminating": "restart",

        # Scheduling terminology
        "scheduled": "scheduling",
        "schedule": "scheduling",
        "schedules": "scheduling",

        # Image-pull terminology
        "download": "pull",
        "downloads": "pull",
        "downloading": "pull",
        "downloaded": "pull",

        # Dependency connectivity terminology
        "connect": "connection",
        "connects": "connection",
        "connected": "connection",
        "connecting": "connection",
        "connections": "connection",
        "timeouts": "timeout",
        "hostnames": "hostname",
        "databases": "database",

        # Readiness terminology
        "ready": "readiness",
        "checks": "check",
        "replicas": "replica",
    }

    token = synonyms.get(token, token)

    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    elif token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("es") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 3:
        token = token[:-1]

    return token
