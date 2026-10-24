# Dependency Connection Failures

Use this runbook when an application cannot connect to a database, API, message queue, or another required service.

## Problem

An application fails to start or operate because a required external dependency is unavailable or unreachable.

## Symptoms

- Application logs report connection refused, timeout, or DNS resolution errors.
- Database connections fail.
- Requests to a required API fail.
- Application readiness checks fail because a dependency is unavailable.
- Containers restart after failing to initialize a dependency.

## Common Causes

- Dependency service is unavailable.
- Incorrect hostname, port, or connection URL.
- DNS resolution failure.
- Network policy or firewall blocks traffic.
- Invalid credentials or expired credentials.
- TLS or certificate configuration errors.
- Required environment variables or Secrets are missing.

## Diagnosis Steps

1. Inspect application logs for the exact connection error.
2. Verify the dependency hostname, port, and service configuration.
3. Check whether the dependency service and endpoints are available.
4. Verify the application configuration and referenced Secrets.
5. Review network policies and connectivity restrictions.
6. Check TLS settings and credentials when indicated by the error.

## Useful Commands

Inspect application logs:

```bash
kubectl logs <pod-name> -n <namespace>
```

Inspect pod events and configuration:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Check services:

```bash
kubectl get services -n <namespace>
```

Check service endpoints:

```bash
kubectl get endpoints -n <namespace>
```

Check configuration resource names without exposing secret values:

```bash
kubectl get configmap,secret -n <namespace>
```

## Remediation

- Correct the hostname, port, or connection URL if misconfigured.
- Restore the dependency service if unavailable.
- Resolve DNS or network-policy problems when confirmed.
- Verify required Secrets and credentials without printing sensitive values.
- Correct TLS settings when certificate errors are present.

Do not assume the database itself is down merely because the application cannot connect.

## Suggested Response

Identify the affected workload and dependency, cite the observed connection error, recommend the next diagnostic checks, and distinguish confirmed causes from possible causes.

## Related Symptoms

- Database connection failure
- Connection refused
- Connection timeout
- DNS resolution failure
- API unavailable
- Message queue connection failure
- Missing connection string
- Dependency unavailable