# Pending Pods And Scheduling Failures

Use this runbook when Kubernetes pods remain in `Pending`, are marked `Unschedulable`, or cannot be scheduled because of insufficient CPU, memory, storage, or node constraints.

## Problem

The Kubernetes scheduler cannot place a pod on an eligible node, preventing the workload from starting.

## Symptoms

- Pod status remains `Pending`.
- Pod conditions report `PodScheduled=False`.
- Events contain `FailedScheduling` or `Insufficient cpu`.
- Events contain `Insufficient memory`.
- Deployment replicas remain unavailable because pods cannot be scheduled.
- Pods cannot find nodes matching their resource or placement requirements.

## Common Causes

- **Insufficient CPU:** Pod CPU requests exceed available node CPU capacity.
- **Insufficient memory:** Pod memory requests exceed available node memory capacity.
- **ResourceQuota or LimitRange:** Namespace resource constraints prevent scheduling or pod creation.
- **Node taints and tolerations:** No eligible node tolerates the pod's taints.
- **Node selectors or affinity:** Placement rules exclude available nodes.
- **Storage constraints:** Persistent volumes cannot bind or required storage is unavailable.

## Diagnosis Steps

1. Inspect pod status and scheduling events.
2. Check whether events report `Insufficient cpu`, `Insufficient memory`, or another scheduling constraint.
3. Compare pod resource requests with node allocatable resources.
4. Check namespace quotas and limits.
5. Review node taints, pod tolerations, node selectors, and affinity rules.
6. Verify persistent volume claims and storage classes when storage is involved.

## Useful Commands

List pods and their status:

```bash
kubectl get pods -n <namespace>
```

Inspect scheduling failures:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Check node capacity and allocatable resources:

```bash
kubectl describe nodes
```

Review namespace resource quotas:

```bash
kubectl get resourcequota,limitrange -n <namespace>
```

Inspect persistent volume claims:

```bash
kubectl get pvc -n <namespace>
```

Review recent scheduling events:

```bash
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

## Remediation

- Reduce CPU or memory requests only when the workload's actual requirements permit it.
- Increase available cluster capacity or scale the node pool when resources are insufficient.
- Adjust quotas or limits when the namespace configuration is the confirmed constraint.
- Correct taints, tolerations, node selectors, or affinity rules when placement constraints are incorrect.
- Resolve persistent volume or storage class issues when storage prevents scheduling.

Do not change resource requests, cluster capacity, or placement rules until the scheduling events identify the constraint.

## Suggested Response

When answering a scheduling question:

1. Identify the affected pod and namespace.
2. Report the exact scheduling reason from pod events.
3. Distinguish CPU shortage, memory shortage, quota limits, placement constraints, and storage problems.
4. Recommend the relevant diagnostic command.
5. Suggest remediation only when supported by the observed evidence.

## Related Symptoms

- `Pending`
- `Unschedulable`
- `FailedScheduling`
- `Insufficient cpu`
- `Insufficient memory`
- CPU resource shortage
- Memory resource shortage
- Node capacity exhausted
- ResourceQuota exceeded
- Persistent volume pending