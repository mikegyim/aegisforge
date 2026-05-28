"""AegisForge HTTP control plane.

Wires together:
- specialized inspection agents
- remediation planner
- digital twin simulator
- LLM reasoning engine
- persistent incident memory + similarity search
- GitOps pull-request generation
- structured logging, Prometheus metrics, OpenTelemetry tracing
- API-key auth, rate limiting, request IDs, security headers
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from . import __version__
from .agents import AgentRouter
from .ai import ReasoningEngine
from .config import get_settings
from .gitops import propose_pull_request
from .llm import build_provider
from .memory import IncidentMemory
from .models import IncidentAnalysis, InfrastructureEvent, PullRequestProposal
from .observability import (
    EVENTS_INGESTED,
    INCIDENT_RISK,
    LLM_LATENCY,
    PR_PROPOSED,
    configure_logging,
    configure_tracing,
)
from .remediation import RemediationPlanner
from .security import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    require_api_key,
)
from .simulation import DigitalTwinSimulator

log = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await _app.state.memory.init()
        log.info(
            "aegisforge.startup",
            environment=settings.environment,
            llm_provider=settings.llm_provider,
            github_dry_run=settings.github_dry_run,
        )
        yield
        await _app.state.memory.close()

    app = FastAPI(
        title="AegisForge API",
        description="Autonomous AI cloud operations and defense platform",
        version=__version__,
        lifespan=lifespan,
    )

    # State
    app.state.settings = settings
    app.state.router = AgentRouter()
    app.state.planner = RemediationPlanner()
    app.state.simulator = DigitalTwinSimulator()
    app.state.reasoning = ReasoningEngine(provider=build_provider(settings))
    app.state.memory = IncidentMemory(settings.database_url)

    # Middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limit
    limiter = Limiter(key_func=get_remote_address, default_limits=[
        f"{settings.rate_limit_per_minute}/minute"
    ])
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _ratelimit_handler(_request: Request, exc: RateLimitExceeded):
        return JSONResponse(status_code=429, content={"detail": f"rate limit exceeded: {exc}"})

    # Metrics + tracing
    if settings.enable_metrics:
        Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    configure_tracing(settings, app)

    auth_dep = Depends(require_api_key(settings))

    # ----- routes -------------------------------------------------------------
    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "aegisforge-api", "version": __version__}

    @app.get("/agents", tags=["meta"])
    async def list_agents() -> dict[str, list[str]]:
        return {"agents": app.state.router.agent_names}

    @app.get("/simulation/graph", tags=["meta"])
    async def simulation_graph() -> dict:
        return app.state.simulator.to_dict()

    @app.post(
        "/events",
        response_model=IncidentAnalysis,
        tags=["ingest"],
        dependencies=[auth_dep],
    )
    async def ingest_event(event: InfrastructureEvent, request: Request) -> IncidentAnalysis:
        rid = getattr(request.state, "request_id", "-")
        log.info("event.received", request_id=rid, event_id=event.event_id, signal=event.signal)

        EVENTS_INGESTED.labels(event.event_type.value, event.severity.value).inc()

        findings = await app.state.router.run(event)
        plan = await app.state.planner.plan(event, findings)
        simulation = await app.state.simulator.simulate(
            plan,
            cluster=event.cluster,
            namespace=event.namespace,
            workload=event.workload,
        )
        similar = await app.state.memory.find_similar(
            signal=event.signal, message=event.message, cluster=event.cluster
        )

        start = time.perf_counter()
        analysis = await app.state.reasoning.analyze(event, findings, plan, simulation, similar)
        LLM_LATENCY.labels(analysis.llm_provider).observe(time.perf_counter() - start)
        INCIDENT_RISK.observe(simulation.risk_score)

        await app.state.memory.remember(analysis)
        log.info(
            "incident.analyzed",
            request_id=rid,
            incident_id=analysis.incident_id,
            risk=simulation.risk_score,
            blast_radius=simulation.estimated_blast_radius,
        )
        return analysis

    @app.post(
        "/incidents/{incident_id}/pull-request",
        response_model=PullRequestProposal,
        tags=["gitops"],
        dependencies=[auth_dep],
    )
    async def propose_pr(incident_id: str) -> PullRequestProposal:
        raw = await app.state.memory.get(incident_id)
        if not raw:
            raise HTTPException(404, "incident not found")
        analysis = IncidentAnalysis.model_validate(raw)
        proposal = await propose_pull_request(analysis, app.state.settings)
        PR_PROPOSED.labels(str(proposal.dry_run).lower()).inc()
        return proposal

    @app.get("/incidents", tags=["incidents"])
    async def list_incidents(limit: int = 50) -> list[dict]:
        return await app.state.memory.list_recent(limit=min(limit, 200))

    @app.get("/incidents/{incident_id}", tags=["incidents"])
    async def get_incident(incident_id: str) -> dict:
        raw = await app.state.memory.get(incident_id)
        if not raw:
            raise HTTPException(404, "incident not found")
        return raw

    return app


app = create_app()
