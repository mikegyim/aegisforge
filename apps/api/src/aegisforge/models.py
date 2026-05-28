"""Pydantic v2 domain models shared across the API."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class EventType(str, Enum):
    observability = "observability"
    security = "security"
    cost = "cost"
    compliance = "compliance"


class InfrastructureEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=3, max_length=128)
    event_type: EventType
    cluster: str = Field(min_length=1, max_length=128)
    namespace: str | None = Field(default=None, max_length=128)
    workload: str | None = Field(default=None, max_length=128)
    severity: Severity
    signal: str = Field(min_length=3, max_length=256)
    message: str = Field(min_length=3, max_length=4096)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class AgentFinding(BaseModel):
    agent: str
    summary: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    risk_score: int = Field(ge=0, le=100)
    tags: list[str] = Field(default_factory=list)


class SimulationResult(BaseModel):
    status: str = Field(
        default="passed",
        pattern="^(passed|passed_with_approval_required|blocked)$",
    )
    estimated_blast_radius: str
    affected_resources: list[str] = Field(default_factory=list)
    policy_violations: list[str] = Field(default_factory=list)
    risk_score: int = Field(ge=0, le=100, default=0)
    safe_to_auto_apply: bool = False
    notes: list[str] = Field(default_factory=list)


class RemediationPlan(BaseModel):
    title: str
    risk: str = Field(default="low", pattern="^(low|medium|high)$")
    actions: list[str]
    requires_approval: bool = True
    gitops_patch: dict[str, Any] = Field(default_factory=dict)
    rollback_plan: list[str] = Field(default_factory=list)
    estimated_recovery_seconds: int = 0


class SimilarIncident(BaseModel):
    incident_id: str
    event_id: str
    cluster: str
    signal: str
    similarity: float
    executive_summary: str
    created_at: datetime


class IncidentAnalysis(BaseModel):
    incident_id: str
    event: InfrastructureEvent
    findings: list[AgentFinding]
    root_cause_hypothesis: str
    remediation_plan: RemediationPlan
    simulation: SimulationResult
    executive_summary: str
    similar_incidents: list[SimilarIncident] = Field(default_factory=list)
    pull_request_url: str | None = None
    llm_provider: str = "mock"
    llm_model: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class PullRequestProposal(BaseModel):
    repository: str
    branch: str
    base: str
    title: str
    body: str
    files: dict[str, str]  # path -> content
    dry_run: bool = True
    url: str | None = None
