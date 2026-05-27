from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


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
    event_id: str = Field(min_length=3)
    event_type: EventType
    cluster: str = Field(min_length=1)
    namespace: str | None = None
    workload: str | None = None
    severity: Severity
    signal: str = Field(min_length=3)
    message: str = Field(min_length=3)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentFinding(BaseModel):
    agent: str
    summary: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    risk_score: int = Field(ge=0, le=100)


class RemediationPlan(BaseModel):
    title: str
    risk: str
    actions: list[str]
    requires_approval: bool = True
    gitops_patch: dict[str, Any] = Field(default_factory=dict)


class IncidentAnalysis(BaseModel):
    event: InfrastructureEvent
    findings: list[AgentFinding]
    root_cause_hypothesis: str
    remediation_plan: RemediationPlan
    executive_summary: str
