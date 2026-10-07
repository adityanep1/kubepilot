"""Grounded answer synthesis for retrieved runbook context."""

import os
from dataclasses import dataclass
from typing import Protocol

from agent.answers.prompts import (
    build_grounded_answer_prompt,
    citations_from_matches,
)
from agent.llm import (
    AzureOpenAILLMClient,
    DeterministicLLMClient,
    HTTPJSONLLMClient,
    LLMClient,
    OpenAICompatibleLLMClient,
)
from agent.state.chat import Citation
from rag import RetrievedDocument


@dataclass(frozen=True)
class GroundedAnswer:
    """Answer text and cited source titles."""

    answer: str
    sources: tuple[str, ...]
    citations: tuple[Citation, ...] = ()


class AnswerSynthesizer(Protocol):
    """Interface for answer synthesis implementations."""

    async def synthesize(
        self,
        *,
        message: str,
        matches: list[RetrievedDocument],
        diagnosis_context: str | None = None,
    ) -> GroundedAnswer:
        """Build an answer from a user message and retrieved context."""


class GroundedAnswerSynthesizer:
    """Synthesize concise answers grounded in retrieved runbook chunks."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or DeterministicLLMClient()

    async def synthesize(
        self,
        *,
        message: str,
        matches: list[RetrievedDocument],
        diagnosis_context: str | None = None,
    ) -> GroundedAnswer:
        """Return a concise source-grounded answer."""

        sources = _source_titles(matches)
        base_answer = _base_answer(message, diagnosis_context)

        if not matches:
            return GroundedAnswer(
                answer=f"{base_answer} No matching runbook was found yet.".strip(),
                sources=(),
            )

        prompt = build_grounded_answer_prompt(
            message=message,
            matches=matches,
            diagnosis_context=diagnosis_context,
        )

        model_answer = await self._llm_client.complete(prompt)
        citations = citations_from_matches(matches)
        source_list = ", ".join(sources)

        answer = f"{base_answer} {model_answer} Sources: {source_list}.".strip()

        return GroundedAnswer(
            answer=answer,
            sources=sources,
            citations=citations,
        )


def create_answer_synthesizer() -> AnswerSynthesizer:
    """Create the configured answer synthesizer."""

    provider = os.getenv("KUBEPILOT_LLM_PROVIDER", "deterministic")

    if provider == "deterministic":
        return GroundedAnswerSynthesizer()

    if provider == "http":
        return _create_http_synthesizer()

    if provider == "openai":
        return _create_openai_synthesizer()

    if provider == "azure_openai":
        return _create_azure_openai_synthesizer()

    raise ValueError(f"Unsupported LLM provider: {provider}")


def _base_answer(
    message: str,
    diagnosis_context: str | None,
) -> str:
    """Build the optional question prefix."""

    if diagnosis_context:
        return ""

    return f'KubePilot received your question: "{message}".'


def _create_http_synthesizer() -> AnswerSynthesizer:
    """Create an HTTP-based answer synthesizer."""

    endpoint = os.getenv("KUBEPILOT_LLM_ENDPOINT")

    if not endpoint:
        raise ValueError(
            "KUBEPILOT_LLM_ENDPOINT is required when "
            "KUBEPILOT_LLM_PROVIDER=http"
        )

    return GroundedAnswerSynthesizer(
        HTTPJSONLLMClient(endpoint)
    )


def _create_openai_synthesizer() -> AnswerSynthesizer:
    """Create an OpenAI-compatible answer synthesizer."""

    api_key = (
        os.getenv("KUBEPILOT_LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    model = os.getenv("KUBEPILOT_LLM_MODEL")

    missing = []

    if not api_key:
        missing.append("KUBEPILOT_LLM_API_KEY")

    if not model:
        missing.append("KUBEPILOT_LLM_MODEL")

    if missing:
        raise ValueError(
            "KUBEPILOT_LLM_API_KEY and KUBEPILOT_LLM_MODEL are required "
            "when KUBEPILOT_LLM_PROVIDER=openai. "
            f"Missing: {', '.join(missing)}"
        )

    endpoint = (
        os.getenv("KUBEPILOT_LLM_ENDPOINT")
        or "https://api.openai.com/v1/chat/completions"
    )

    return GroundedAnswerSynthesizer(
        OpenAICompatibleLLMClient(
            api_key,
            model,
            endpoint=endpoint,
        )
    )


def _create_azure_openai_synthesizer() -> AnswerSynthesizer:
    """Create an Azure OpenAI answer synthesizer."""

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    missing = []

    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY")

    if not endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")

    if not deployment:
        missing.append("AZURE_OPENAI_DEPLOYMENT")

    if missing:
        raise ValueError(
            "Azure OpenAI configuration is incomplete. Missing: "
            + ", ".join(missing)
        )

    api_version = os.getenv(
        "AZURE_OPENAI_API_VERSION",
        "2024-02-01",
    )

    return GroundedAnswerSynthesizer(
        AzureOpenAILLMClient(
            api_key,
            endpoint,
            deployment,
            api_version=api_version,
        )
    )


def _source_titles(
    matches: list[RetrievedDocument],
) -> tuple[str, ...]:
    """Return unique source titles while preserving retrieval order."""

    unique_titles: list[str] = []

    for match in matches:
        title = match.document.title

        if title not in unique_titles:
            unique_titles.append(title)

    return tuple(unique_titles)