# AegisForge

**AegisForge** is an autonomous AI cloud operations and defense platform built for Kubernetes, DevSecOps, SRE, and GenAI infrastructure engineering.

Built by **Michael Opoku-Gyimah** / GitHub: [`mikegyim`](https://github.com/mikegyim)

## What This Project Demonstrates

AegisForge combines:

- Kubernetes platform engineering
- AI agents and RAG-based incident reasoning
- DevSecOps automation
- GitOps-style remediation workflows
- Infrastructure-as-Code
- Security event analysis
- Observability-driven incident response
- Simulation-based remediation testing

This is designed as a serious portfolio project for senior cloud/platform/DevSecOps/AI infrastructure roles.

## Core Features

- Real-time infrastructure event ingestion
- AI incident analysis and summarization
- Policy-aware remediation planning
- Autonomous GitOps remediation proposal generation
- Security alert classification
- Kubernetes digital twin simulation
- Prometheus/Grafana-ready metrics endpoints
- REST API built with FastAPI
- Agent framework for observability, security, governance, cost, and remediation
- Docker, Kubernetes, Helm, Terraform, and GitHub Actions included

## Architecture

```text
External Events
    |
    v
FastAPI Control Plane
    |
    +--> Event Store
    +--> Agent Router
    +--> AI Reasoning Engine
    +--> Remediation Planner
    +--> Simulation Engine
    +--> GitOps Proposal Generator
```

## Local Quickstart

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn aegisforge.main:app --reload
```

Open:

```text
http://localhost:8000/docs
```

## Run Tests

```bash
cd apps/api
pytest -v
```

## Example Event

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d @../../examples/events/node-memory-pressure.json
```

## Roadmap

- [x] API control plane
- [x] Agent orchestration skeleton
- [x] AI incident reasoning abstraction
- [x] Remediation planner
- [x] Simulation engine
- [x] Kubernetes manifests
- [x] Terraform scaffold
- [x] GitHub Actions CI
- [ ] LangGraph multi-agent workflow
- [ ] pgvector incident memory
- [ ] ArgoCD PR automation
- [ ] Falco event integration
- [ ] Prometheus live scraping
- [ ] React topology dashboard

## Resume Bullet

> Built AegisForge, an autonomous AI cloud operations and defense platform using FastAPI, Kubernetes, Terraform, Helm, AI agents, policy checks, simulation-based remediation, and GitOps-style infrastructure automation.
