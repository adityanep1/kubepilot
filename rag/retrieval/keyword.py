"""Simple keyword-based retriever for local runbook search."""

import re
from collections import Counter
from pathlib import Path

from rag.chunking import chunk_markdown
from rag.loaders import load_markdown_documents
from rag.models import Document, RetrievedDocument

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class KeywordRetriever:
    """Rank documents by token overlap with the query."""

    def __init__(self, documents: list[Document]) -> None:
        self._documents = documents

    def search(
        self,
        query: str,
        *,
        limit: int = 3,
    ) -> list[RetrievedDocument]:
        """Return the most relevant unique runbooks for a query."""

        query_terms = _token_counts(query)
        if not query_terms:
            return []

        matches: list[RetrievedDocument] = []

        for document in self._documents:
            score = _score_document(query_terms, document)

            if score > 0:
                matches.append(
                    RetrievedDocument(
                        document=document,
                        score=score,
                    )
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
        query_count * title_terms.get(term, 0)
        for term, query_count in query_terms.items()
    )

    content_score = sum(
        query_count * content_terms.get(term, 0)
        for term, query_count in query_terms.items()
    )

    return (title_score * 5) + content_score


def _token_counts(text: str) -> Counter[str]:
    tokens = TOKEN_PATTERN.findall(text.lower())
    normalized_tokens = [
        _normalize_token(token)
        for token in tokens
    ]
    return Counter(normalized_tokens)


def _normalize_token(token: str) -> str:
    """Normalize simple English variants and domain synonyms."""

    synonyms = {
        "crashing": "restart",
        "crash": "restart",
        "dying": "restart",
        "terminate": "restart",
        "terminated": "restart",
        "terminating": "restart",
        "scheduled": "scheduling",
        "schedule": "scheduling",
        "schedules": "scheduling",
    }

    token = synonyms.get(token, token)

    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"

    if token.endswith("ing") and len(token) > 5:
        token = token[:-3]

    if token.endswith("es") and len(token) > 4:
        token = token[:-2]

    elif token.endswith("s") and len(token) > 3:
        token = token[:-1]

    return token