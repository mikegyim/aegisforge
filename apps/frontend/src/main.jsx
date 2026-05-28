import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity, AlertTriangle, Brain, GitPullRequest, ShieldCheck, Zap,
} from 'lucide-react';
import './style.css';

const API = '/api';

const DEMOS = [
  {
    label: 'CI runner OOM',
    event: {
      event_id: 'evt-demo-mem',
      event_type: 'observability',
      cluster: 'dev-us-east-1',
      namespace: 'ci',
      workload: 'gitlab-runner',
      severity: 'critical',
      signal: 'node_memory_pressure',
      message: 'OOMKilled on gitlab-runner after CI workload spike',
      metadata: { source: 'frontend-demo' },
    },
  },
  {
    label: 'Reverse shell in pod',
    event: {
      event_id: 'evt-demo-sec',
      event_type: 'security',
      cluster: 'prod-eu-west-1',
      namespace: 'platform',
      workload: 'api-gateway',
      severity: 'critical',
      signal: 'shell_in_pod',
      message: 'Falco detected exec /bin/sh from api-gateway pod',
      metadata: { source: 'frontend-demo' },
    },
  },
  {
    label: 'Cost anomaly',
    event: {
      event_id: 'evt-demo-cost',
      event_type: 'cost',
      cluster: 'dev-us-east-1',
      namespace: 'platform',
      workload: 'auth',
      severity: 'warning',
      signal: 'cost_anomaly',
      message: 'Daily cost for auth exceeded budget by 38%',
      metadata: { source: 'frontend-demo' },
    },
  },
];

function App() {
  const [incidents, setIncidents] = useState([]);
  const [graph, setGraph] = useState(null);
  const [selected, setSelected] = useState(null);
  const [agents, setAgents] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    try {
      const [a, g, i] = await Promise.all([
        fetch(`${API}/agents`).then((r) => r.json()),
        fetch(`${API}/simulation/graph`).then((r) => r.json()),
        fetch(`${API}/incidents`).then((r) => r.json()),
      ]);
      setAgents(a.agents || []);
      setGraph(g);
      setIncidents(Array.isArray(i) ? i : []);
    } catch (e) { setError(String(e)); }
  }

  useEffect(() => { refresh(); }, []);

  async function runDemo(demo) {
    setLoading(true); setError(null);
    try {
      const event = { ...demo.event, event_id: `${demo.event.event_id}-${Date.now()}` };
      const resp = await fetch(`${API}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event),
      });
      if (!resp.ok) throw new Error(`API ${resp.status}: ${await resp.text()}`);
      const analysis = await resp.json();
      setSelected(analysis);
      refresh();
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  }

  async function proposePR(incidentId) {
    setLoading(true); setError(null);
    try {
      const resp = await fetch(`${API}/incidents/${incidentId}/pull-request`, { method: 'POST' });
      if (!resp.ok) throw new Error(`API ${resp.status}: ${await resp.text()}`);
      const pr = await resp.json();
      setSelected((s) => s ? { ...s, _pr: pr } : s);
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  }

  const stats = useMemo(() => {
    const total = incidents.length;
    const high = incidents.filter((i) => i.severity === 'critical').length;
    const security = incidents.filter((i) => i.event_type === 'security').length;
    return { total, high, security, agents: agents.length };
  }, [incidents, agents]);

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand"><span className="dot" /> AegisForge Control Plane</div>
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>v0.2 · {agents.length} agents online</div>
      </div>

      <section className="hero">
        <h1>Autonomous AI cloud operations and defense</h1>
        <p>
          Ingest infrastructure events, run them through a multi-agent inspection pipeline, reason
          over the findings with an LLM, simulate the blast radius against a digital twin, and open
          a GitOps pull request - all behind a human approval gate.
        </p>
        <div className="row">
          {DEMOS.map((d) => (
            <button key={d.label} className="primary" disabled={loading} onClick={() => runDemo(d)}>
              <Zap size={14} style={{ verticalAlign: -2, marginRight: 6 }} />
              {d.label}
            </button>
          ))}
          <button className="secondary" onClick={refresh}>Refresh</button>
        </div>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      </section>

      <section className="grid">
        <div className="card kpi">
          <h3>Incidents analyzed</h3>
          <div className="big">{stats.total}</div>
        </div>
        <div className="card kpi">
          <h3>Critical</h3>
          <div className="big" style={{ color: 'var(--danger)' }}>{stats.high}</div>
        </div>
        <div className="card kpi">
          <h3>Security events</h3>
          <div className="big" style={{ color: 'var(--warning)' }}>{stats.security}</div>
        </div>
        <div className="card kpi">
          <h3>Active agents</h3>
          <div className="big" style={{ color: 'var(--accent-2)' }}>{stats.agents}</div>
        </div>
      </section>

      <section className="section">
        <h2>Recent incidents</h2>
        <div className="feed">
          {incidents.length === 0 && <div className="card">No incidents yet. Run a demo above.</div>}
          {incidents.map((it) => (
            <div className="item" key={it.incident_id}
                 onClick={() => fetch(`${API}/incidents/${it.incident_id}`).then((r) => r.json()).then(setSelected)}
                 style={{ cursor: 'pointer' }}>
              <div>
                <div className="title">{it.plan_title}</div>
                <div className="meta">
                  {it.cluster} · {it.namespace}/{it.workload} · {it.signal} ·
                  {' '}{new Date(it.created_at).toLocaleString()}
                </div>
              </div>
              <span className={`badge ${it.severity}`}>{it.severity}</span>
            </div>
          ))}
        </div>
      </section>

      {selected && (
        <section className="section">
          <h2>Incident #{selected.incident_id?.slice(0, 8)}</h2>
          <div className="panel">
            <h3>Executive summary</h3>
            <p>{selected.executive_summary}</p>
            <h3>Root cause hypothesis</h3>
            <p>{selected.root_cause_hypothesis}</p>

            <h3>Agent findings</h3>
            <div className="findings">
              {selected.findings?.map((f) => (
                <div className="finding" key={f.agent}>
                  <div>
                    <div className="agent">{f.agent}</div>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>{f.summary}</div>
                  </div>
                  <div style={{ color: 'var(--muted)' }}>conf {(f.confidence * 100).toFixed(0)}%</div>
                  <div className="risk" style={{ color: f.risk_score > 70 ? 'var(--danger)' : 'var(--ok)' }}>
                    {f.risk_score}
                  </div>
                </div>
              ))}
            </div>

            <h3>Digital twin simulation</h3>
            <div>
              status: <code>{selected.simulation?.status}</code> · blast radius:{' '}
              <code>{selected.simulation?.estimated_blast_radius}</code> · risk:{' '}
              <strong>{selected.simulation?.risk_score}/100</strong>
            </div>
            <div className="simbar"><span style={{ width: `${selected.simulation?.risk_score || 0}%` }} /></div>
            {selected.simulation?.policy_violations?.length > 0 && (
              <div style={{ color: 'var(--danger)', marginTop: 8 }}>
                <AlertTriangle size={14} style={{ verticalAlign: -2 }} /> policy violations:
                <ul>{selected.simulation.policy_violations.map((v) => <li key={v}>{v}</li>)}</ul>
              </div>
            )}

            <h3>Remediation plan</h3>
            <ul>{selected.remediation_plan?.actions?.map((a, i) => <li key={i}>{a}</li>)}</ul>

            <div style={{ marginTop: 12, display: 'flex', gap: 10, alignItems: 'center' }}>
              <button className="primary" onClick={() => proposePR(selected.incident_id)}>
                <GitPullRequest size={14} style={{ verticalAlign: -2, marginRight: 6 }} /> Propose pull request
              </button>
              {selected._pr && (
                <span style={{ color: 'var(--muted)' }}>
                  PR: <code>{selected._pr.url}</code>
                </span>
              )}
            </div>

            <h3 style={{ marginTop: 18 }}>Raw analysis</h3>
            <pre>{JSON.stringify(selected, null, 2)}</pre>
          </div>
        </section>
      )}

      <section className="section">
        <h2>Cluster digital twin</h2>
        <div className="panel">
          <div style={{ color: 'var(--muted)', marginBottom: 10 }}>
            cluster: <code>{graph?.cluster}</code> · namespaces: <code>{graph?.namespaces?.join(', ')}</code>
          </div>
          {graph?.deployments?.map((d) => (
            <div className="finding" key={`${d.namespace}/${d.name}`}>
              <div>
                <div className="agent">{d.namespace}/{d.name}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  replicas {d.replicas} · {d.has_pdb ? 'PDB ✓' : 'no PDB'} ·
                  {' '}{d.has_resource_limits ? 'limits ✓' : 'no limits'}
                  {d.serves?.length ? ` · serves: ${d.serves.join(', ')}` : ''}
                </div>
              </div>
              <div />
              <div />
            </div>
          ))}
        </div>
      </section>

      <footer>
        AegisForge · <ShieldCheck size={12} style={{ verticalAlign: -2 }} /> approval-required by default ·
        {' '}<a href="https://github.com/mikegyim/aegisforge">github.com/mikegyim/aegisforge</a>
      </footer>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
