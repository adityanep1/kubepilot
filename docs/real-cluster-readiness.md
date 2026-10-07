# Real Cluster Readiness

KubePilot defaults to fixture mode so the demo is repeatable. Real cluster mode
is available when you want the API to inspect live Kubernetes deployments, pods,
events, and logs.

## Modes

| Mode | Use when | Required setting |
| --- | --- | --- |
| `fixture` | local demo, CI, screenshots | `KUBEPILOT_K8S_MODE=fixture` |
| `kubeconfig` | running API on your laptop against a cluster | `KUBEPILOT_K8S_MODE=kubeconfig` |
| `in_cluster` | running KubePilot inside Kubernetes | `KUBEPILOT_K8S_MODE=in_cluster` |

The Go tool service has its own mode:

| Mode | Use when | Required setting |
| --- | --- | --- |
| `fixture` | deterministic local service output | `KUBEPILOT_K8S_TOOL_MODE=fixture` |
| `cluster` | live cluster reads through the tool service | `KUBEPILOT_K8S_TOOL_MODE=cluster` |

## Kubeconfig Mode

Use this mode when running the API locally against a real cluster.

```bash
export KUBEPILOT_K8S_MODE=kubeconfig
export KUBEPILOT_KUBECONFIG="$HOME/.kube/config"
export KUBEPILOT_ALLOWED_NAMESPACES=payments,platform,notifications
export KUBEPILOT_ALLOWED_ACTIONS=cluster:health,deployment:diagnose,deployment:incident-report,deployment:remediation-plan
uvicorn kubepilot_api.main:app --reload