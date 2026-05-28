from aegisforge.ai import ReasoningEngine
from aegisforge.llm import MockProvider
from aegisforge.models import (
    AgentFinding,
    EventType,
    InfrastructureEvent,
    RemediationPlan,
    Severity,
    SimulationResult,
)


def _event(event_type=EventType.observability, signal="node_memory_pressure",
           message="OOM"):
    return InfrastructureEvent(
        event_id="evt-ai-1",
        event_type=event_type,
        cluster="dev-us-east-1",
        namespace="ci",
        workload="gitlab-runner",
        severity=Severity.critical,
        signal=signal,
        message=message,
    )


async def test_mock_provider_produces_security_aware_cause():
    engine = ReasoningEngine(provider=MockProvider())
    event = _event(event_type=EventType.security, signal="shell_in_pod",
                   message="reverse shell exec")
    findings = [AgentFinding(agent="security-agent", summary="anomaly",
                              confidence=0.9, evidence=["shell"], risk_score=90, tags=["security"])]
    plan = RemediationPlan(title="Quarantine", risk="high", actions=["isolate"])
    sim = SimulationResult(estimated_blast_radius="workload-level", risk_score=70)
    analysis = await engine.analyze(event, findings, plan, sim)
    assert analysis.llm_provider == "mock"
    assert "security" in analysis.root_cause_hypothesis.lower() or \
           "compromise" in analysis.root_cause_hypothesis.lower()


async def test_engine_dedupes_recommended_actions():
    engine = ReasoningEngine(provider=MockProvider())
    findings = [AgentFinding(agent="observability-agent", summary="ok",
                             confidence=0.7, evidence=["OOM"], risk_score=85)]
    plan = RemediationPlan(title="Raise memory", risk="medium",
                           actions=["Raise memory requests/limits and restart the deployment."])
    sim = SimulationResult(estimated_blast_radius="workload-level", risk_score=30)
    analysis = await engine.analyze(_event(), findings, plan, sim)
    # the mock recommendation overlaps with plan; no dupes
    assert len(set(analysis.remediation_plan.actions)) == len(analysis.remediation_plan.actions)
