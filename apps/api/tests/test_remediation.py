from aegisforge.models import EventType, InfrastructureEvent, Severity
from aegisforge.remediation import RemediationPlanner, plan_to_helm_values_yaml


def _evt(**overrides):
    base = dict(
        event_id="evt-1",
        event_type=EventType.observability,
        cluster="dev-us-east-1",
        namespace="ci",
        workload="gitlab-runner",
        severity=Severity.critical,
        signal="node_memory_pressure",
        message="OOM event for gitlab-runner",
    )
    base.update(overrides)
    return InfrastructureEvent(**base)


async def test_memory_plan_emits_deployment_patch():
    plan = await RemediationPlanner().plan(_evt())
    assert plan.risk == "medium"
    assert plan.gitops_patch["kind"] == "Deployment"
    assert plan.rollback_plan
    yaml_out = plan_to_helm_values_yaml(plan)
    assert "memory" in yaml_out


async def test_security_plan_emits_networkpolicy():
    plan = await RemediationPlanner().plan(
        _evt(event_type=EventType.security, signal="shell_in_pod",
             message="Reverse shell exec detected")
    )
    assert plan.risk == "high"
    assert plan.gitops_patch["kind"] == "NetworkPolicy"


async def test_cost_plan_rightsizes():
    plan = await RemediationPlanner().plan(_evt(event_type=EventType.cost, signal="cost_anomaly",
                                                message="cost spike", severity=Severity.warning))
    assert "right-size" in plan.title.lower() or "right size" in plan.title.lower()


async def test_default_plan_is_investigation():
    plan = await RemediationPlanner().plan(_evt(severity=Severity.info, signal="generic"))
    assert plan.risk == "low"
    assert "investigation" in plan.title.lower()
