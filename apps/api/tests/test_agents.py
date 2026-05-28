from aegisforge.agents import (
    AgentRouter,
    CostAgent,
    GovernanceAgent,
    ObservabilityAgent,
    SecurityAgent,
)
from aegisforge.models import EventType, InfrastructureEvent, Severity


def _evt(**overrides):
    base = dict(
        event_id="evt-1",
        event_type=EventType.observability,
        cluster="dev-us-east-1",
        namespace="ci",
        workload="gitlab-runner",
        severity=Severity.critical,
        signal="node_memory_pressure",
        message="OOM in gitlab-runner due to memory pressure",
    )
    base.update(overrides)
    return InfrastructureEvent(**base)


async def test_observability_tags_memory():
    f = await ObservabilityAgent().inspect(_evt())
    assert f.agent == "observability-agent"
    assert "memory" in f.tags
    assert f.risk_score == 85


async def test_security_explicit_event_high_risk():
    f = await SecurityAgent().inspect(
        _evt(event_type=EventType.security, signal="shell_in_pod",
             message="Reverse shell exec detected in pod")
    )
    assert f.risk_score == 90
    assert "security" in f.tags


async def test_security_keyword_hit_when_observability():
    f = await SecurityAgent().inspect(
        _evt(message="kubectl exec leak detected on pod")
    )
    assert f.risk_score >= 70
    assert "security" in f.tags


async def test_governance_prod_cluster_higher_risk():
    f = await GovernanceAgent().inspect(_evt(cluster="prod-eu-west-1"))
    assert f.risk_score >= 60


async def test_cost_agent_flags_cost_event():
    f = await CostAgent().inspect(_evt(event_type=EventType.cost))
    assert "cost" in f.tags


async def test_router_runs_all_agents_concurrently():
    findings = await AgentRouter().run(_evt())
    names = {f.agent for f in findings}
    assert names == {
        "observability-agent",
        "security-agent",
        "governance-agent",
        "cost-agent",
    }
