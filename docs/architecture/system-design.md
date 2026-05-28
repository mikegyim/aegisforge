# System Design

AegisForge is a control plane that turns infrastructure events into reviewable,
simulated, policy-checked GitOps changes - with humans on the merge button.

## Components

```
+---------------------------------------------------------------+
|                       FastAPI control plane                   |
|                                                               |
|  POST /events ---> AgentRouter (obs, sec, gov, cost)          |
|                   |          (concurrent rule-based inspection)|
|                   v                                            |
|              RemediationPlanner --------------+                |
|                   |                           |                |
|                   v                           v                |
|         DigitalTwinSimulator        IncidentMemory             |
|         (cluster graph, blast       (SQLite, similarity)       |
|          radius, policy check)                                  |
|                   \                  /                          |
|                    v                v                           |
|                ReasoningEngine (LLM)                            |
|                       |                                         |
|                       v                                         |
|                IncidentAnalysis  --->  /incidents               |
|                       |                                         |
|                       v                                         |
|              GitOps proposer (PyGithub) ---> draft PR           |
+---------------------------------------------------------------+
            ^                                       ^
            | events                                | metrics
            |                                       |
       AegisForgeWorker                          Prometheus
       (queue + retry)                           Grafana / OTLP
```

## Safety model

- All plans default to `requires_approval = true`. The flag is read by the
  simulator and surfaced in the API response.
- The simulator pre-checks plans against the OPA policy in
  `security/policies/`; violations short-circuit the plan to `blocked`.
- The PR generator runs in dry-run mode unless `AEGIS_GITHUB_TOKEN` *and*
  `AEGIS_GITHUB_REPOSITORY` are set *and* `AEGIS_GITHUB_DRY_RUN=false`.

## Extensibility

- **New agents**: subclass `BaseAgent`, append to `AgentRouter`.
- **New LLM providers**: subclass `LLMProvider`, add a case to `build_provider`.
- **New event sources**: implement a worker that pushes to `EventQueue`.
- **New PR targets**: implement the `GithubClient` protocol (GitLab, Bitbucket).

## Why a digital twin?

Mutating real clusters from an LLM output is dangerous. The twin gives the
planner a cheap, deterministic place to estimate blast radius and catch policy
violations before they hit admission control.
