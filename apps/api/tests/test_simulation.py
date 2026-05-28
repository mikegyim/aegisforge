from aegisforge.models import RemediationPlan
from aegisforge.simulation import ClusterGraph, Deployment, DigitalTwinSimulator


def _graph():
    return ClusterGraph(
        cluster="dev-us-east-1",
        namespaces=["ci", "platform"],
        deployments=[
            Deployment(name="gitlab-runner", namespace="ci", replicas=3, has_pdb=False),
            Deployment(name="api-gateway", namespace="platform", replicas=2,
                       has_pdb=True, has_resource_limits=True, serves=["auth"]),
            Deployment(name="auth", namespace="platform", replicas=2, has_pdb=True),
        ],
    )


async def test_read_only_plan_is_safe():
    sim = DigitalTwinSimulator(graph=_graph())
    plan = RemediationPlan(title="Investigate", actions=["Collect logs", "Check metrics"])
    result = await sim.simulate(plan, cluster="dev-us-east-1",
                                namespace="ci", workload="gitlab-runner")
    assert result.status == "passed"
    assert result.safe_to_auto_apply is True


async def test_high_risk_plan_requires_approval():
    sim = DigitalTwinSimulator(graph=_graph())
    plan = RemediationPlan(
        title="Drain node",
        risk="high",
        actions=["Drain node and evict pods", "Delete daemonset"],
    )
    result = await sim.simulate(plan, cluster="dev-us-east-1",
                                namespace="ci", workload="gitlab-runner")
    assert result.status == "passed_with_approval_required"
    assert result.estimated_blast_radius.startswith("namespace")


async def test_policy_violation_blocks():
    sim = DigitalTwinSimulator(graph=_graph())
    plan = RemediationPlan(
        title="Apply deployment without memory limit",
        risk="medium",
        actions=["apply deployment"],
        gitops_patch={
            "kind": "Deployment",
            "spec": {"template": {"spec": {"containers": [{"name": "bad", "resources": {}}]}}},
        },
    )
    result = await sim.simulate(plan, cluster="dev-us-east-1",
                                namespace="ci", workload="gitlab-runner")
    assert result.status == "blocked"
    assert any("memory" in v for v in result.policy_violations)


async def test_blast_radius_includes_downstreams():
    sim = DigitalTwinSimulator(graph=_graph())
    plan = RemediationPlan(title="Roll auth deployment", actions=["roll deployment"])
    result = await sim.simulate(plan, cluster="dev-us-east-1",
                                namespace="platform", workload="auth")
    affected = "\n".join(result.affected_resources)
    assert "platform/auth" in affected
    assert "platform/api-gateway" in affected
