import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ShieldCheck, Activity, Brain, GitPullRequest } from 'lucide-react';
import './style.css';

function App() {
  const [analysis, setAnalysis] = useState(null);

  async function runDemo() {
    const resp = await fetch('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_id: 'evt-demo-001',
        event_type: 'observability',
        cluster: 'dev-us-east-1',
        namespace: 'ci',
        workload: 'gitlab-runner',
        severity: 'critical',
        signal: 'node_memory_pressure',
        message: 'Memory pressure detected after CI workload spike',
        metadata: { source: 'frontend-demo' }
      })
    });
    setAnalysis(await resp.json());
  }

  return (
    <main>
      <section className="hero">
        <h1>AegisForge</h1>
        <p>Autonomous AI cloud operations and defense platform.</p>
        <button onClick={runDemo}>Run AI Incident Demo</button>
      </section>

      <section className="grid">
        <Card icon={<Activity />} title="Observability" text="Analyze metrics, logs, and Kubernetes events." />
        <Card icon={<ShieldCheck />} title="Security" text="Classify suspicious runtime and audit events." />
        <Card icon={<Brain />} title="AI Reasoning" text="Generate root-cause hypotheses and incident summaries." />
        <Card icon={<GitPullRequest />} title="GitOps" text="Produce remediation proposals for approval." />
      </section>

      {analysis && (
        <section className="panel">
          <h2>Incident Analysis</h2>
          <pre>{JSON.stringify(analysis, null, 2)}</pre>
        </section>
      )}
    </main>
  );
}

function Card({ icon, title, text }) {
  return (
    <div className="card">
      <div className="icon">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
