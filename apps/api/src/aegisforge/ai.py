from .models import InfrastructureEvent, AgentFinding, RemediationPlan, IncidentAnalysis


class ReasoningEngine:
    async def analyze(
        self,
        event: InfrastructureEvent,
        findings: list[AgentFinding],
        plan: RemediationPlan,
    ) -> IncidentAnalysis:
        evidence = "; ".join(e for f in findings for e in f.evidence) or event.message
        root_cause = (
            f"{event.signal} in {event.cluster}"
            if event.event_type != "security"
            else f"Potential security anomaly: {event.signal}"
        )

        summary = (
            f"AegisForge detected a {event.severity.value} {event.event_type.value} event "
            f"on cluster {event.cluster}. Primary signal: {event.signal}. "
            f"Recommended plan: {plan.title}."
        )

        return IncidentAnalysis(
            event=event,
            findings=findings,
            root_cause_hypothesis=f"{root_cause}. Evidence: {evidence}",
            remediation_plan=plan,
            executive_summary=summary,
        )
