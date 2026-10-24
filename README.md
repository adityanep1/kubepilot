 <p align="center">
  <img src="web/kubepilot-icon.svg" alt="KubePilot logo" width="96" />
</p>

<h1 align="center">KubePilot</h1>

<p align="center">
  An AI assistant for understanding and troubleshooting Kubernetes workloads.
</p>

<p align="center">
  <a href="#try-the-demo">Try the demo</a> ·
  <a href="#develop-locally">Develop locally</a> ·
  <a href="#repository-guide">Repository guide</a>
</p>

---

## What is KubePilot?

KubePilot gives Kubernetes operators one place to ask questions, inspect cluster evidence, find relevant runbooks, diagnose deployments, and create incident reports.

It is designed to support human decisions, not replace them. Answers are built from observable signals and documented runbooks so an operator can review the evidence behind a recommendation.

## Try the demo

### Requirements

- Git
- Docker Engine with the Docker Compose plugin

Verify your installation:

```bash
docker --version
docker compose version
```

### Start the demo

From the repository root, run:

```bash
docker compose up --build
```

Wait for the services to become healthy, then open the web interface:

**http://localhost:3000**

The API is available at **http://localhost:8000**.

To stop the demo, press `Ctrl + C` in the terminal running Docker Compose, then run:

```bash
docker compose down
```

## Develop locally

### Requirements

- Python
- Docker
- kubectl
- Helm
- kind (for local Kubernetes deployment)

### Run the test suite

From the repository root:

```bash
python -m pytest -q
```

### Validate the Helm chart

```bash
helm lint ./helm/kubepilot
```

## Deploy to a local Kubernetes cluster

The following steps describe the validated local `kind` deployment using fixture mode.

### 1. Build the Docker image

```bash
docker build -t kubepilot-api:latest .
```

### 2. Create a local cluster if needed

Check whether the cluster already exists:

```bash
kind get clusters
```

If `kubepilot` is not listed, create it:

```bash
kind create cluster --name kubepilot
```

### 3. Load the image into the cluster

```bash
kind load docker-image kubepilot-api:latest --name kubepilot
```

### 4. Deploy with Helm

```bash
helm upgrade --install kubepilot ./helm/kubepilot
```

### 5. Check the deployment

```bash
kubectl get nodes
kubectl get pods
```

The KubePilot pod should reach `1/1 Running`.

### 6. Verify the API

Start port forwarding:

```bash
kubectl port-forward service/kubepilot-kubepilot 8000:8000
```

Keep that terminal open. In a second PowerShell terminal, run:

```powershell
Invoke-RestMethod http://localhost:8000/healthz
Invoke-RestMethod http://localhost:8000/readyz
Invoke-RestMethod http://localhost:8000/api/v1/status
```

The health endpoint should report `ok`, and the readiness endpoint should report `ready`.

**Important:** The default Helm configuration uses fixture mode and deterministic agent behavior. This validates local deployment and API availability; it does not validate integration with a real Kubernetes workload cluster.

## Repository guide

- `agent/` — agent and answer-generation components
- `rag/` — document retrieval and evaluation
- `services/` — API and supporting services
- `docs/runbooks/` — operational runbooks
- `helm/` — Kubernetes Helm chart
- `gitops/` — GitOps configuration
- `monitoring/` — monitoring configuration
- `tests/` — automated tests
- `web/` — web interface and assets

## Project status

KubePilot's automated test suite passes, and its API has been deployed and checked on a local `kind` cluster in fixture mode. Real-cluster workload integration remains future validation work.
