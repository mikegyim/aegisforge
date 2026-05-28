import pytest

from aegisforge.memory import IncidentMemory
from aegisforge.models import (
    AgentFinding,
    EventType,
    IncidentAnalysis,
    InfrastructureEvent,
    RemediationPlan,
    Severity,
    SimulationResult,
)


def _analysis(incident_id: str, signal: str, message: str) -> IncidentAnalysis:
    event = InfrastructureEvent(
        event_id=incident_id,
        event_type=EventType.observability,
        cluster="dev-us-east-1",
        namespace="ci",
        workload="gitlab-runner",
        severity=Severity.critical,
        signal=signal,
        message=message,
    )
    findings = [AgentFinding(agent="observability-agent", summary="ok",
                             confidence=0.8, evidence=[message], risk_score=80, tags=["memory"])]
    plan = RemediationPlan(title="Increase memory", risk="medium",
                           actions=["raise memory limit"], rollback_plan=["revert"])
    sim = SimulationResult(estimated_blast_radius="workload-level", risk_score=40)
    return IncidentAnalysis(
        incident_id=incident_id,
        event=event,
        findings=findings,
        root_cause_hypothesis="memory pressure",
        remediation_plan=plan,
        simulation=sim,
        executive_summary=f"summary for {incident_id}",
    )


@pytest.fixture
async def mem():
    m = IncidentMemory("sqlite+aiosqlite:///:memory:")
    await m.init()
    yield m
    await m.close()


async def test_remember_and_get(mem):
    a = _analysis("evt-mem-1", "node_memory_pressure", "OOM detected in gitlab-runner")
    await mem.remember(a)
    raw = await mem.get(a.incident_id)
    assert raw is not None
    assert raw["incident_id"] == a.incident_id


async def test_list_recent_orders_by_time(mem):
    for i in range(3):
        await mem.remember(_analysis(f"evt-mem-{i}", "node_memory_pressure", "OOM event"))
    rows = await mem.list_recent(limit=10)
    assert len(rows) == 3


async def test_find_similar_returns_overlap(mem):
    await mem.remember(_analysis("evt-mem-a", "node_memory_pressure",
                                  "OOM in gitlab-runner due to memory pressure"))
    await mem.remember(_analysis("evt-mem-b", "cpu_throttling",
                                  "CPU throttling on api-gateway"))
    similar = await mem.find_similar(
        signal="node_memory_pressure",
        message="OOM detected after memory pressure spike",
        cluster="dev-us-east-1",
        top_k=3,
    )
    assert similar
    assert similar[0].event_id == "evt-mem-a"
    assert similar[0].similarity > 0.15
