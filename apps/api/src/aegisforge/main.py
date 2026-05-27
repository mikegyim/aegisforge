from fastapi import FastAPI

from .agents import AgentRouter
from .ai import ReasoningEngine
from .models import InfrastructureEvent, IncidentAnalysis
from .remediation import RemediationPlanner
from .simulation import DigitalTwinSimulator

app = FastAPI(
    title="AegisForge API",
    description="Autonomous AI cloud operations and defense platform",
    version="0.1.0",
)

router = AgentRouter()
planner = RemediationPlanner()
reasoning = ReasoningEngine()
simulator = DigitalTwinSimulator()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegisforge-api"}


@app.post("/events", response_model=IncidentAnalysis)
async def ingest_event(event: InfrastructureEvent) -> IncidentAnalysis:
    findings = await router.run(event)
    plan = await planner.plan(event)
    simulation = await simulator.simulate(plan)
    analysis = await reasoning.analyze(event, findings, plan)
    analysis.remediation_plan.gitops_patch["simulation"] = simulation
    return analysis


@app.get("/agents")
async def list_agents() -> dict[str, list[str]]:
    return {
        "agents": [
            "observability-agent",
            "security-agent",
            "governance-agent",
            "remediation-planner",
            "digital-twin-simulator",
        ]
    }
