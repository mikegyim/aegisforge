"""Remediation planning - turns events + findings into a structured plan.

The planner is rule-driven so the contract is predictable. The LLM layer can
*augment* the action list, but the structural fields (risk, gitops_patch,
rollback_plan) are produced by code so they can be policy-checked.
"""

from __future__ import annotations

from typing import Any

import yaml

from .agents import _MEMORY_KEYWORDS, _SECURITY_KEYWORDS
from .models import AgentFinding, EventType, InfrastructureEvent, RemediationPlan, Severity


class RemediationPlanner:
    def __init__(self) -> None:
        pass

    async def plan(
        self,
        event: InfrastructureEvent,
        findings: list[AgentFinding] | None = None,
    ) -> RemediationPlan:
        findings = findings or []
        security_risk = any(
            "security" in f.tags or (f.risk_score >= 80 and f.agent == "security-agent")
            for f in findings
        )
        text = event.signal + " " + event.message

        if (
            event.event_type == EventType.security
            or security_risk
            or _SECURITY_KEYWORDS.search(text)
        ):
            return self._security_quarantine(event)

        if event.severity == Severity.critical and _MEMORY_KEYWORDS.search(text):
            return self._memory_increase(event)

        if event.event_type == EventType.cost:
            return self._cost_rightsize(event)

        return self._investigate(event)

    # ----- plan templates -----------------------------------------------------
    def _security_quarantine(self, event: InfrastructureEvent) -> RemediationPlan:
        workload = event.workload or "workload"
        ns = event.namespace or "default"
        patch: dict[str, Any] = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": f"aegisforge-quarantine-{workload}", "namespace": ns},
            "spec": {
                "podSelector": {"matchLabels": {"app": workload}},
                "policyTypes": ["Ingress", "Egress"],
                "ingress": [],
                "egress": [],
            },
        }
        return RemediationPlan(
            title=f"Quarantine workload {workload} and open security review",
            risk="high",
            actions=[
                "Apply NetworkPolicy isolation to quarantine the workload",
                "Capture pod logs and Kubernetes audit events for forensics",
                "Scale suspicious workload to zero after human approval",
                "Open incident ticket for security review",
            ],
            requires_approval=True,
            gitops_patch=patch,
            rollback_plan=[
                "Delete the quarantine NetworkPolicy",
                "Restore workload replicas to prior value",
            ],
            estimated_recovery_seconds=900,
        )

    def _memory_increase(self, event: InfrastructureEvent) -> RemediationPlan:
        workload = event.workload or "workload"
        ns = event.namespace or "default"
        patch = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": workload, "namespace": ns},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": workload,
                                "resources": {
                                    "requests": {"memory": "512Mi", "cpu": "250m"},
                                    "limits": {"memory": "1Gi", "cpu": "1"},
                                },
                            }
                        ]
                    }
                }
            },
        }
        return RemediationPlan(
            title=f"Raise memory limits and restart {workload}",
            risk="medium",
            actions=[
                "Raise memory requests to 512Mi and limits to 1Gi",
                "Roll the deployment to apply new limits",
                "Watch OOMKilled events for 15 minutes",
                "Open a pull request with the Helm values update",
            ],
            requires_approval=True,
            gitops_patch=patch,
            rollback_plan=[
                "Revert deployment to previous resource limits",
                "Rollout undo deployment",
            ],
            estimated_recovery_seconds=300,
        )

    def _cost_rightsize(self, event: InfrastructureEvent) -> RemediationPlan:
        workload = event.workload or "workload"
        return RemediationPlan(
            title=f"Right-size {workload} resources to reduce cost",
            risk="low",
            actions=[
                "Compare requested vs actual resource usage over 7 days",
                "Propose new resource requests at p95 utilization",
                "Open pull request with Helm values update",
            ],
            requires_approval=True,
            gitops_patch={},
            rollback_plan=["Revert Helm values"],
            estimated_recovery_seconds=600,
        )

    def _investigate(self, event: InfrastructureEvent) -> RemediationPlan:
        return RemediationPlan(
            title="Open investigation with recommended diagnostic commands",
            risk="low",
            actions=[
                (
                    f"kubectl -n {event.namespace or 'default'} "
                    f"describe pod {event.workload or '<workload>'}"
                ),
                (
                    f"kubectl -n {event.namespace or 'default'} "
                    f"logs {event.workload or '<workload>'} --tail=200"
                ),
                "Check Prometheus metrics for the workload",
                "Compare against historical incident memory",
            ],
            requires_approval=True,
            gitops_patch={},
            rollback_plan=[],
            estimated_recovery_seconds=0,
        )


def plan_to_helm_values_yaml(plan: RemediationPlan) -> str:
    """Render the structural part of a plan as a Helm values diff."""

    patch = plan.gitops_patch or {}
    # If we proposed a NetworkPolicy, ship it as a values overlay
    if patch.get("kind") == "NetworkPolicy":
        return yaml.safe_dump(
            {"networkPolicy": {"enabled": True, "spec": patch.get("spec", {})}},
            sort_keys=False,
        )
    if patch.get("kind") == "Deployment":
        spec = patch.get("spec", {}).get("template", {}).get("spec", {})
        containers = spec.get("containers", [])
        resources = containers[0].get("resources", {}) if containers else {}
        return yaml.safe_dump({"resources": resources}, sort_keys=False)
    return yaml.safe_dump({"actions": plan.actions}, sort_keys=False)
