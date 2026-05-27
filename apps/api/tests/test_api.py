from fastapi.testclient import TestClient
from aegisforge.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_event_analysis_memory_pressure() -> None:
    payload = {
        "event_id": "evt-001",
        "event_type": "observability",
        "cluster": "dev-us-east-1",
        "namespace": "ci",
        "workload": "gitlab-runner",
        "severity": "critical",
        "signal": "node_memory_pressure",
        "message": "Node memory pressure detected after CI workload spike",
        "metadata": {"node": "ip-10-0-1-10"},
    }
    resp = client.post("/events", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "AegisForge detected" in data["executive_summary"]
    assert data["remediation_plan"]["requires_approval"] is True
    assert len(data["findings"]) >= 3


def test_agents_list() -> None:
    resp = client.get("/agents")
    assert resp.status_code == 200
    assert "security-agent" in resp.json()["agents"]
