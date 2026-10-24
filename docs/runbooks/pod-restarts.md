# Pod Restarts

Use this runbook when a Kubernetes pod or container restarts unexpectedly, repeatedly, or enters `CrashLoopBackOff`.

## Problem

A workload repeatedly restarts and may become unavailable or degraded.

## Symptoms

- Pod restart count is greater than zero.
- Container enters `CrashLoopBackOff`.
- Application availability decreases after a deployment.
- Container exits shortly after startup.
- Pod events show probe failures or container termination.

## Evidence to Check

1. Check pod status and restart count.
2. Read previous container logs.
3. Describe the pod and review warning events.
4. Check the container termination reason and exit code.
5. Look for `OOMKilled` or memory-related events.
6. Check liveness and startup probes.
7. Compare restart times with recent deployments.
8. Check configuration, Secrets, and ConfigMaps.
9. Verify required environment variables and dependencies.

## Useful Commands

List pods and restart counts:

```bash
kubectl get pods -n <namespace>
```

Inspect a pod:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Read current logs:

```bash
kubectl logs <pod-name> -n <namespace>
```

Read logs from the previous container:

```bash
kubectl logs <pod-name> -n <namespace> --previous
```

Check recent events:

```bash
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

Inspect container termination details:

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
```

## Common Causes and Resolutions

### Application Crash

**Evidence:** Previous logs contain exceptions, errors, or panic messages.

**Resolution:** Inspect previous logs, identify the application error, and review recent code or configuration changes.

### Missing Configuration

**Evidence:** Logs mention missing environment variables, Secrets, or ConfigMaps.

**Resolution:** Compare the deployment configuration with the application's required settings and verify referenced resources.

### Liveness Probe Failure

**Evidence:** Pod events report liveness probe failures.

**Resolution:** Verify the health endpoint, port, probe timings, and application startup behavior before changing probe settings.

### Out of Memory

**Evidence:** Container termination reason is `OOMKilled`, or events indicate memory pressure.

**Resolution:** Review memory requests and limits, application memory usage, and possible memory leaks.

### Dependency Failure

**Evidence:** Logs show connection failures to databases, APIs, queues, or other services.

**Resolution:** Verify dependency availability, connectivity, credentials, and recent configuration changes.

## Troubleshooting Order

1. Check pod status and restart count.
2. Inspect previous container logs.
3. Review pod events.
4. Check termination reason and exit code.
5. Investigate probe failures and memory limits.
6. Verify configuration and dependencies.
7. Compare the failure timeline with recent changes.

## Suggested Response

When answering a pod restart question:

1. Identify the affected pod and namespace.
2. Describe the observed restart behavior.
3. State the likely cause only when supported by evidence.
4. Cite the relevant logs, events, or container state.
5. Recommend specific diagnostic commands or next steps.
6. State when the available evidence is insufficient to determine the root cause.

Prefer previous container logs when investigating a container that has already restarted.

## Related Symptoms

- `CrashLoopBackOff`
- `OOMKilled`
- Liveness or startup probe failure
- Container termination
- Application crash
- Missing environment variable
- Missing Secret or ConfigMap
- Dependency connection failure