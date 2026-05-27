from .models import InfrastructureEvent, RemediationPlan, EventType, Severity


class RemediationPlanner:
    async def plan(self, event: InfrastructureEvent) -> RemediationPlan:
        if event.event_type == EventType.security:
            return RemediationPlan(
                title="Quarantine suspicious workload and open security review",
                risk="high",
                actions=[
                    "Apply network policy isolation",
                    "Scale suspicious workload to zero after approval",
                    "Collect pod logs and Kubernetes audit events",
                    "Create incident ticket for security review",
                ],
                requires_approval=True,
                gitops_patch={
                    "kind": "NetworkPolicy",
                    "metadata": {"name": f"quarantine-{event.workload or 'workload'}"},
                },
            )

        if event.severity == Severity.critical and "memory" in event.signal.lower():
            return RemediationPlan(
                title="Increase workload memory limit and restart deployment",
                risk="medium",
                actions=[
                    "Increase memory requests and limits",
                    "Restart affected deployment",
                    "Watch OOMKilled events for 15 minutes",
                    "Open pull request with Helm values update",
                ],
                requires_approval=True,
                gitops_patch={
                    "resources": {
                        "requests": {"memory": "512Mi"},
                        "limits": {"memory": "1Gi"},
                    }
                },
            )

        return RemediationPlan(
            title="Open investigation with recommended diagnostic commands",
            risk="low",
            actions=[
                "Collect recent Kubernetes events",
                "Review workload logs",
                "Check Prometheus metrics",
                "Compare against historical incident memory",
            ],
            requires_approval=True,
        )
