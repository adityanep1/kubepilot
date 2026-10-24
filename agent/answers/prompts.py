"""Prompt construction for grounded runbook answers."""

from agent.state.chat import Citation
from rag import RetrievedDocument



def build_grounded_answer_prompt(
    *,
    message: str,
    matches: list[RetrievedDocument],
    diagnosis_context: str | None = None,
) -> str:
    """Build a grounded RAG prompt from retrieved runbook chunks."""

    context_parts = []

    for index, match in enumerate(matches, start=1):
        content = match.document.content.strip()
        title = match.document.title

        context_parts.append(
            f"[{index}] {title}\n"
            f"Source: {match.document.source}\n\n"
            f"{content}"
        )

    context = "\n\n---\n\n".join(context_parts)

    diagnosis = (
        diagnosis_context
        or "No Kubernetes diagnosis evidence was provided."
    )

    return (
        "You are KubePilot, a Kubernetes operations assistant.\n"
        "Answer only from the supplied runbook context and Kubernetes evidence. "
        "If context is missing, say no matching runbook was found.\n\n"
        f"QUESTION:\n{message}\n\n"
        f"RUNBOOK CONTEXT:\n{context}\n\n"
        f"KUBERNETES EVIDENCE:\n{diagnosis}\n\n"
        "RESPONSE REQUIREMENTS:\n"
        "- Preserve Markdown headings, lists, and code fences from the context.\n"
        "- Keep commands inside fenced code blocks.\n"
        "- Do not flatten multiple lines into one paragraph.\n"
        "- Be concise and provide actionable operational steps.\n"
        "- Cite source numbers when making runbook-backed claims.\n"
        "- Do not invent Kubernetes evidence or claim commands were executed."
    )



def citations_from_matches(matches: list[RetrievedDocument]) -> tuple[Citation, ...]:
    """Create citations from retrieved documents."""

    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()

    for match in matches:
        key = (match.document.title, match.document.source)

        if key in seen:
            continue

        seen.add(key)

        citations.append(
            Citation(
                title=match.document.title,
                source=match.document.source,
                snippet=_snippet(match.document.content),
            )
        )

    return tuple(citations)


def _snippet(content: str, *, max_length: int = 4000) -> str:
    """Preserve runbook Markdown while limiting excessively large content."""
    content = content.strip()

    if len(content) <= max_length:
        return content

    return content[:max_length].rstrip() + "\n\n[Content truncated]"
