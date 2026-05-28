from aegisforge.config import Settings
from aegisforge.gitops import build_proposal, propose_pull_request, render_pr_body
from aegisforge.models import (
    AgentFinding,
    EventType,
    IncidentAnalysis,
    InfrastructureEvent,
    RemediationPlan,
    Severity,
    SimulationResult,
)


def _analysis() -> IncidentAnalysis:
    event = InfrastructureEvent(
        event_id="evt-pr-1",
        event_type=EventType.observability,
        cluster="dev-us-east-1",
        namespace="ci",
        workload="gitlab-runner",
        severity=Severity.critical,
        signal="node_memory_pressure",
        message="OOM event",
    )
    findings = [AgentFinding(agent="observability-agent", summary="ok",
                             confidence=0.8, evidence=["OOM event"], risk_score=85, tags=["memory"])]
    plan = RemediationPlan(
        title="Raise memory limits",
        risk="medium",
        actions=["raise memory limits"],
        rollback_plan=["revert"],
        gitops_patch={
            "kind": "Deployment",
            "spec": {"template": {"spec": {"containers": [
                {"name": "gitlab-runner",
                 "resources": {"requests": {"memory": "512Mi"}, "limits": {"memory": "1Gi"}}}
            ]}}},
        },
    )
    sim = SimulationResult(estimated_blast_radius="workload-level", risk_score=35,
                           status="passed_with_approval_required")
    return IncidentAnalysis(
        incident_id="incident-pr-1",
        event=event, findings=findings,
        root_cause_hypothesis="memory pressure",
        remediation_plan=plan, simulation=sim,
        executive_summary="needs more memory",
    )


def test_render_pr_body_contains_key_sections():
    body = render_pr_body(_analysis())
    assert "Executive summary" in body
    assert "Digital twin simulation" in body
    assert "Rollback plan" in body


def test_build_proposal_uses_helm_values_layout():
    settings = Settings(github_repository="mikegyim/aegisforge", github_dry_run=True)
    p = build_proposal(_analysis(), settings)
    assert p.dry_run
    assert "values.yaml" in next(iter(p.files))


class _StubClient:
    def __init__(self):
        self.opened = None

    def open_pull_request(self, proposal):
        self.opened = proposal
        return "https://github.com/example/pull/42"


async def test_propose_uses_client_when_not_dry_run():
    settings = Settings(
        github_repository="mikegyim/aegisforge",
        github_token="fake",
        github_dry_run=False,
    )
    stub = _StubClient()
    result = await propose_pull_request(_analysis(), settings, client=stub)
    assert result.url == "https://github.com/example/pull/42"
    assert stub.opened is not None


async def test_propose_returns_dry_run_url_by_default():
    settings = Settings(github_repository="mikegyim/aegisforge", github_dry_run=True)
    result = await propose_pull_request(_analysis(), settings)
    assert result.url.startswith("dry-run://")
