import pytest
from fastapi.testclient import TestClient

from aegisforge.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _payload(**overrides):
    base = dict(
        event_id="evt-int-001",
        event_type="observability",
        cluster="dev-us-east-1",
        namespace="ci",
        workload="gitlab-runner",
        severity="critical",
        signal="node_memory_pressure",
        message="Memory pressure detected after CI workload spike",
        metadata={"node": "ip-10-0-1-10"},
    )
    base.update(overrides)
    return base


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_agents_endpoint(client):
    r = client.get("/agents")
    assert r.status_code == 200
    assert "security-agent" in r.json()["agents"]


def test_simulation_graph(client):
    r = client.get("/simulation/graph")
    assert r.status_code == 200
    assert "deployments" in r.json()


def test_event_ingest_returns_analysis(client):
    r = client.post("/events", json=_payload())
    assert r.status_code == 200
    data = r.json()
    assert "AegisForge" in data["executive_summary"]
    assert data["remediation_plan"]["requires_approval"] is True
    assert len(data["findings"]) >= 3
    assert data["simulation"]["estimated_blast_radius"]
    assert data["llm_provider"] == "mock"


def test_event_then_pr_proposal_and_lookup(client):
    r = client.post("/events", json=_payload(event_id="evt-int-002"))
    incident_id = r.json()["incident_id"]

    pr = client.post(f"/incidents/{incident_id}/pull-request")
    assert pr.status_code == 200
    body = pr.json()
    assert body["dry_run"] is True
    assert body["url"].startswith("dry-run://")

    list_r = client.get("/incidents")
    assert list_r.status_code == 200
    assert any(i["incident_id"] == incident_id for i in list_r.json())

    detail = client.get(f"/incidents/{incident_id}")
    assert detail.status_code == 200


def test_metrics_endpoint(client):
    # warm the metric
    client.post("/events", json=_payload(event_id="evt-int-003"))
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "aegisforge_events_ingested_total" in r.text


def test_security_headers_applied(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-ID" in r.headers


def test_api_key_enforced_when_configured(monkeypatch):
    import importlib

    monkeypatch.setenv("AEGIS_API_KEY", "secret-key")
    # Reload config + main to pick up env
    from aegisforge import config
    config.get_settings.cache_clear()
    from aegisforge import main as main_mod
    importlib.reload(main_mod)
    with TestClient(main_mod.create_app()) as c:
        no_key = c.post("/events", json=_payload(event_id="evt-int-auth"))
        assert no_key.status_code == 401
        ok = c.post("/events", json=_payload(event_id="evt-int-auth"),
                    headers={"X-API-Key": "secret-key"})
        assert ok.status_code == 200
    monkeypatch.delenv("AEGIS_API_KEY", raising=False)
    config.get_settings.cache_clear()
