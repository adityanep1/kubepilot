"""LLM client interfaces and local provider implementations."""

import asyncio
import json
import urllib.request
from collections.abc import Callable
from typing import Protocol


class LLMClient(Protocol):
    """Completion interface implemented by language model providers."""

    async def complete(self, prompt: str) -> str:
        """Return a model response for a prompt."""


def _section(prompt: str, name: str) -> str:
    """Extract a named section while preserving multiline content."""
    marker = f"{name}:\n"
    start = prompt.find(marker)
    if start == -1:
        return ""
    start += len(marker)

    headers = (
        "\n\nQUESTION:\n",
        "\n\nRUNBOOK CONTEXT:\n",
        "\n\nKUBERNETES EVIDENCE:\n",
        "\n\nRESPONSE REQUIREMENTS:\n",
    )
    positions = [pos for header in headers if (pos := prompt.find(header, start)) != -1]
    end = min(positions) if positions else len(prompt)
    return prompt[start:end].strip()


class DeterministicLLMClient:
    """Offline-safe LLM stand-in for tests and local development."""

    async def complete(self, prompt: str) -> str:
        """Return focused troubleshooting guidance from known runbooks."""

        question = _section(prompt, "QUESTION")
        context = _section(prompt, "RUNBOOK CONTEXT")
        if not context:
            return "No matching runbook was found yet."

        q = question.lower()

        if "imagepullbackoff" in q or "image pull" in q or "errimagepull" in q:
            title = "Troubleshooting ImagePullBackOff"
            steps = [
                ("Inspect pod events", "kubectl describe pod <pod-name> -n <namespace>"),
                (
                    "Check the configured image",
                    (
                        "kubectl get pod <pod-name> -n <namespace> "
                        "-o jsonpath='{.spec.containers[*].image}'"
                    ),
                ),
                ("Check image-pull secrets", "kubectl get pod <pod-name> -n <namespace> -o yaml"),
            ]
            note = (
                "Check the event messages for an incorrect image name or tag, "
                "registry access problems, or missing image-pull credentials."
            )

        elif "crashloopbackoff" in q or ("crash" in q and "pod" in q):
            title = "Troubleshooting CrashLoopBackOff"
            steps = [
                (
                    "Inspect the pod and its termination reason",
                    "kubectl describe pod <pod-name> -n <namespace>",
                ),
                (
                    "Read logs from the previous container",
                    "kubectl logs <pod-name> -n <namespace> --previous",
                ),
                (
                    "Check recent namespace events",
                    "kubectl get events -n <namespace> --sort-by=.lastTimestamp",
                ),
            ]
            note = (
                "Use the termination reason and previous logs to narrow down "
                "the cause before changing the workload."
            )

        elif "pending" in q or "unschedulable" in q or "not schedul" in q:
            title = "Troubleshooting Pending Pods"
            steps = [
                ("Inspect scheduling events", "kubectl describe pod <pod-name> -n <namespace>"),
                ("Check node capacity and status", "kubectl get nodes"),
                (
                    "Review recent events",
                    "kubectl get events -n <namespace> --sort-by=.lastTimestamp",
                ),
            ]
            note = (
                "Look for insufficient CPU or memory, storage constraints, "
                "node selectors, taints, or unavailable persistent volumes."
            )

        elif "readiness" in q or "probe" in q:
            title = "Troubleshooting Readiness Probe Failures"
            steps = [
                (
                    "Inspect pod events and probe configuration",
                    "kubectl describe pod <pod-name> -n <namespace>",
                ),
                ("Read container logs", "kubectl logs <pod-name> -n <namespace>"),
                (
                    "Inspect the workload configuration",
                    "kubectl get pod <pod-name> -n <namespace> -o yaml",
                ),
            ]
            note = (
                "Verify the probe path, port, timing, and whether the application "
                "is ready to serve traffic."
            )

        elif "deployment" in q or "rollout" in q:
            title = "Troubleshooting Deployment Rollouts"
            steps = [
                (
                    "Check rollout status",
                    "kubectl rollout status deployment/<deployment-name> -n <namespace>",
                ),
                (
                    "Inspect deployment events",
                    "kubectl describe deployment <deployment-name> -n <namespace>",
                ),
                ("Check replica and pod status", "kubectl get pods -n <namespace>"),
            ]
            note = (
                "Check failed replicas, image errors, scheduling events, and "
                "readiness before deciding whether to roll back."
            )

        elif "connection" in q or "dependency" in q or "connect" in q:
            title = "Troubleshooting Dependency Connection Failures"
            steps = [
                ("Check service endpoints", "kubectl get services,endpoints -n <namespace>"),
                ("Inspect affected pod events", "kubectl describe pod <pod-name> -n <namespace>"),
                ("Review application logs", "kubectl logs <pod-name> -n <namespace>"),
            ]
            note = (
                "Verify the service name, target port, endpoints, network policies, "
                "and dependency availability."
            )

        elif "unhealthy" in q or "not healthy" in q:
            title = "Troubleshooting Unhealthy Workloads"
            steps = [
                ("Check pod status", "kubectl get pods -n <namespace>"),
                ("Inspect the affected pod", "kubectl describe pod <pod-name> -n <namespace>"),
                ("Review application logs", "kubectl logs <pod-name> -n <namespace>"),
            ]
            note = (
                "Use pod conditions, events, and logs to determine whether the "
                "problem is scheduling, startup, probes, or application failure."
            )

        elif "restart" in q and ("pod" in q or "kubernetes" in q):
            title = "Troubleshooting Kubernetes Pod Restarts"
            steps = [
                ("Check restart counts and pod status", "kubectl get pods -n <namespace>"),
                (
                    "Inspect pod events and termination reason",
                    "kubectl describe pod <pod-name> -n <namespace>",
                ),
                ("Check current logs", "kubectl logs <pod-name> -n <namespace>"),
                (
                    "Read previous container logs",
                    "kubectl logs <pod-name> -n <namespace> --previous",
                ),
                (
                    "Review recent events",
                    "kubectl get events -n <namespace> --sort-by=.lastTimestamp",
                ),
            ]
            note = "Check the termination reason and logs before changing the workload."

        else:
            return "## Retrieved troubleshooting guidance\n\n" + context

        answer = [f"## {title}", ""]
        for index, (description, command) in enumerate(steps, start=1):
            answer.extend(
                [
                    f"{index}. **{description}:**",
                    "   ```bash",
                    f"   {command}",
                    "   ```",
                    "",
                ]
            )
        answer.append(note)
        answer.extend(
            [
                "",
                "Replace placeholder names such as `<namespace>` and `<pod-name>` "
                "with your actual values. These commands inspect resources; "
                "they do not automatically fix the issue.",
            ]
        )
        return "\n".join(answer)


class HTTPJSONLLMClient:
    """LLM client for self-hosted HTTP JSON completion services."""

    def __init__(
        self,
        endpoint: str,
        *,
        timeout_seconds: float = 10.0,
        transport: Callable[[str], str] | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def complete(self, prompt: str) -> str:
        if self._transport is not None:
            return self._transport(prompt)
        return await asyncio.to_thread(self._complete_sync, prompt)

    def _complete_sync(self, prompt: str) -> str:
        payload = json.dumps({"prompt": prompt}).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint,
            data=payload,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            body = response.read().decode("utf-8")

        data = json.loads(body)
        answer = data.get("answer", data.get("text"))
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError(
                "LLM provider response must include a non-empty answer or text field."
            )
        return answer.strip()


class OpenAICompatibleLLMClient:
    """LLM client for OpenAI-compatible REST APIs."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        endpoint: str = "https://api.openai.com/v1/chat/completions",
        timeout_seconds: float = 30.0,
        transport: Callable[[str], str] | None = None,
        api_version: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._api_version = api_version

    async def complete(self, prompt: str) -> str:
        if self._transport is not None:
            return self._transport(prompt)
        return await asyncio.to_thread(self._complete_sync, prompt)

    def _complete_sync(self, prompt: str) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 250,
        }
        raw_body = json.dumps(payload).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "api-key": self._api_key,
        }
        endpoint = self._endpoint
        if self._api_version:
            separator = "&" if "?" in endpoint else "?"
            endpoint = f"{endpoint}{separator}api-version={self._api_version}"

        request = urllib.request.Request(
            endpoint,
            data=raw_body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            body = response.read().decode("utf-8")

        data = json.loads(body)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI-compatible LLM response did not include any choices.")

        message = choices[0].get("message") or {}
        answer = message.get("content") or choices[0].get("text")
        if isinstance(answer, list):
            answer = "".join(part.get("text", "") for part in answer if isinstance(part, dict))
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError(
                "OpenAI-compatible LLM response must include a non-empty message.content field."
            )
        return answer.strip()


class AzureOpenAILLMClient(OpenAICompatibleLLMClient):
    """LLM client for Azure OpenAI chat completions using deployment names."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str,
        *,
        api_version: str = "2024-02-01",
        timeout_seconds: float = 30.0,
        transport: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(
            api_key,
            deployment,
            endpoint=(f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions"),
            timeout_seconds=timeout_seconds,
            transport=transport,
            api_version=api_version,
        )
