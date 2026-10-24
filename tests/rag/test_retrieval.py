from django.core.serializers import python

from rag.models import Document
from rag.retrieval import KeywordRetriever, VectorRetriever


def test_keyword_retriever_returns_relevant_document() -> None:
    retriever = KeywordRetriever(
        [
            Document(
                source="deployment.md",
                title="Deployment rollout failures",
                content="Pods are in ImagePullBackOff after a rollout.",
            ),
            Document(
                source="restart.md",
                title="Pod restarts",
                content="Check previous logs for CrashLoopBackOff.",
            ),
        ],
    )

    matches = retriever.search("deployment image pull failing")

    assert matches
    assert matches[0].document.title == "Deployment rollout failures"


def test_keyword_retriever_returns_empty_list_for_blank_query() -> None:
    retriever = KeywordRetriever(
        [Document(source="restart.md", title="Pod restarts", content="Check previous logs.")]
    )

    assert retriever.search("   ") == []


def test_vector_retriever_uses_memory_backend_without_faiss() -> None:
    retriever = VectorRetriever(
        [
            Document(
                source="deployment.md",
                title="Deployment rollout failures",
                content="Pods are in ImagePullBackOff after a rollout.",
            ),
            Document(
                source="restart.md",
                title="Pod restarts",
                content="Check previous logs for CrashLoopBackOff.",
            ),
        ],
        prefer_faiss=False,
    )

    matches = retriever.search("image rollout")

    assert retriever.backend == "memory"
    assert matches


def test_database_connection_query_ranks_dependency_runbook_first() -> None:
    retriever = KeywordRetriever(
        [
            Document(
                source="pod-restarts.md",
                title="Pod Restarts",
                content="Investigate restart counts, previous container logs, "
                "CrashLoopBackOff, and OOMKilled containers.",
            ),
            Document(
                source="dependency-connection-failures.md",
                title="Dependency Connection Failures",
                content="Troubleshoot applications unable to connect to a "
                "database, API, or required service. Check connection timeouts, "
                "DNS, hostnames, ports, and credentials.",
            ),
        ],
    )

    matches = retriever.search("application cannot connect to database")

    assert matches
    assert matches[0].document.title == "Dependency Connection Failures"


def test_safe_deployment_restart_query_ranks_rolling_restart_first() -> None:
    retriever = KeywordRetriever(
        [
            Document(
                source="pod-restarts.md",
                title="Pod Restarts",
                content="Investigate unexpected container restarts and "
                "CrashLoopBackOff errors using logs and pod events.",
            ),
            Document(
                source="rolling-restart.md",
                title="Rolling Restart",
                content="Safely restart a Kubernetes deployment using "
                "kubectl rollout restart deployment. Monitor rollout status "
                "and verify pods become ready.",
            ),
        ],
    )

    matches = retriever.search("how do I restart a deployment safely")

    assert matches
    assert matches[0].document.title == "Rolling Restart"
from rag.models import Document
from rag.retrieval import KeywordRetriever


def test_image_pull_query_ranks_image_pull_runbook_first() -> None:
    retriever = KeywordRetriever([
        Document(
            source="deployment-rollout-failures.md",
            title="Deployment rollout failures",
            content="Investigate failed deployments and rollout status.",
        ),
        Document(
            source="image-pull-backoff.md",
            title="Image Pull Backoff",
            content="ImagePullBackOff occurs when Kubernetes cannot pull an image.",
        ),
    ])

    matches = retriever.search("How do I fix ImagePullBackOff?")
    assert matches
    assert matches[0].document.title == "Image Pull Backoff"


def test_pending_query_ranks_scheduling_runbook_first() -> None:
    retriever = KeywordRetriever([
        Document(
            source="pod-restarts.md",
            title="Pod Restarts",
            content="Investigate restarted containers and previous logs.",
        ),
        Document(
            source="pending-pods-scheduling.md",
            title="Pending Pods And Scheduling Failures",
            content="Troubleshoot Pending and Unschedulable pods.",
        ),
    ])

    matches = retriever.search("Why are my pods Pending?")
    assert matches
    assert matches[0].document.title == "Pending Pods And Scheduling Failures"


def test_deployment_rollout_query_ranks_rollout_runbook_first() -> None:
    retriever = KeywordRetriever([
        Document(
            source="readiness-probe-failures.md",
            title="Readiness Probe Failures",
            content="Investigate failed readiness probes.",
        ),
        Document(
            source="deployment-rollout-failures.md",
            title="Deployment rollout failures",
            content="Investigate failed deployment rollouts and replicas.",
        ),
    ])

    matches = retriever.search("Why is my deployment rollout failing?")
    assert matches
    assert matches[0].document.title == "Deployment rollout failures"


def test_readiness_query_ranks_readiness_runbook_first() -> None:
    retriever = KeywordRetriever([
        Document(
            source="pod-restarts.md",
            title="Pod Restarts",
            content="Investigate restart counts and previous logs.",
        ),
        Document(
            source="readiness-probe-failures.md",
            title="Readiness Probe Failures",
            content="Troubleshoot failing readiness probes and health checks.",
        ),
    ])

    matches = retriever.search("Why is my readiness probe failing?")
    assert matches
    assert matches[0].document.title == "Readiness Probe Failures"


def test_private_registry_auth_query_ranks_image_pull_first() -> None:
    retriever = KeywordRetriever(
        [
            Document(
                source="unhealthy-workloads.md",
                title="Unhealthy Workloads",
                content="Investigate unhealthy pods and failed replicas.",
            ),
            Document(
                source="image-pull-backoff.md",
                title="Image Pull Backoff",
                content=(
                    "Troubleshoot private registry authentication, "
                    "image pull errors, and imagePullSecrets."
                ),
            ),
        ],
    )

    matches = retriever.search(
        "private registry authentication failed"
    )

    assert matches
    assert matches[0].document.title == "Image Pull Backoff"