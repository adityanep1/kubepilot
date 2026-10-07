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

KubePilot gives Kubernetes operators one place to ask questions, inspect cluster
evidence, find relevant runbooks, diagnose deployments, and create incident
reports.

It is designed to support human decisions, not replace them. Answers are built
from observable signals and documented runbooks so an operator can review the
evidence behind a recommendation.

## Try the demo

### Requirements

- Git
- Docker Engine with the Docker Compose plugin

Check that Docker is installed and running:

```bash
docker --version
docker compose version