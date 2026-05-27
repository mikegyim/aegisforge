# AegisForge System Design

## Control Plane

The API receives infrastructure, security, compliance, and cost events.

## Agent Layer

Agents inspect the event from different perspectives:

- Observability Agent
- Security Agent
- Governance Agent
- Cost Agent
- Remediation Agent

## Reasoning Layer

The reasoning layer creates:

- incident summary
- root cause hypothesis
- remediation plan
- GitOps patch proposal

## Safety Model

AegisForge defaults to approval-based remediation.

Autonomous mutation is disabled unless explicitly enabled.
