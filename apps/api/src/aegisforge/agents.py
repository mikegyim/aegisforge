"""Specialized inspection agents.

Each agent inspects an :class:`InfrastructureEvent` from a different lens and
emits an :class:`AgentFinding`. Agents are intentionally rule-driven (cheap,
deterministic, testable) and feed evidence into the LLM reasoning layer rather
than calling the LLM themselves on every inspection.
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod

from .models import AgentFinding, EventType, InfrastructureEvent, Severity


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def inspect(self, event: InfrastructureEvent) -> AgentFinding: ...


_SECURITY_KEYWORDS = re.compile(
    r"\b(?:shell|exec|reverse|nc\s|netcat|crypto|mining|cve|exploit|"
    r"privilege|escalation|kubectl|kube-apiserver|secret|token|leak)\b",
    re.IGNORECASE,
)
_MEMORY_KEYWORDS = re.compile(r"\b(?:oom|oomkilled|memory|rss|page\s?fault)\b", re.IGNORECASE)
_CPU_KEYWORDS = re.compile(r"\b(?:cpu|throttl|saturat)\b", re.IGNORECASE)
_NETWORK_KEYWORDS = re.compile(r"\b(?:network|egress|ingress|dns|latency)\b", re.IGNORECASE)


class ObservabilityAgent(BaseAgent):
    name = "observability-agent"

    async def inspect(self, event: InfrastructureEvent) -> AgentFinding:
        tags: list[str] = []
        if _MEMORY_KEYWORDS.search(event.signal + " " + event.message):
            tags.append("memory")
        if _CPU_KEYWORDS.search(event.signal + " " + event.message):
            tags.append("cpu")
        if _NETWORK_KEYWORDS.search(event.signal + " " + event.message):
            tags.append("network")

        severity_score = {Severity.info: 25, Severity.warning: 55, Severity.critical: 85}
        risk = severity_score[event.severity]
        confidence = 0.6 + 0.05 * len(tags)

        return AgentFinding(
            agent=self.name,
            summary=f"Observed {event.signal} on {event.cluster}",
            confidence=min(confidence, 0.95),
            evidence=[
                event.message,
                f"cluster={event.cluster}",
                f"workload={event.workload or 'unknown'}",
                f"namespace={event.namespace or 'unknown'}",
            ],
            risk_score=risk,
            tags=tags or ["generic"],
        )


class SecurityAgent(BaseAgent):
    name = "security-agent"

    async def inspect(self, event: InfrastructureEvent) -> AgentFinding:
        text = event.signal + " " + event.message
        explicit = event.event_type == EventType.security
        keyword_hit = bool(_SECURITY_KEYWORDS.search(text))
        suspicious = explicit or keyword_hit

        risk = 90 if explicit else (70 if keyword_hit else 15)
        confidence = 0.9 if explicit else (0.7 if keyword_hit else 0.4)

        return AgentFinding(
            agent=self.name,
            summary=(
                "Security anomaly indicators present"
                if suspicious
                else "No direct security indicator"
            ),
            confidence=confidence,
            evidence=[
                event.message,
                f"event_type={event.event_type.value}",
                f"keyword_match={'yes' if keyword_hit else 'no'}",
            ],
            risk_score=risk,
            tags=["security"] if suspicious else [],
        )


class GovernanceAgent(BaseAgent):
    name = "governance-agent"

    async def inspect(self, event: InfrastructureEvent) -> AgentFinding:
        prod_ish = (event.cluster or "").lower().startswith(("prod", "production"))
        risk = 60 if prod_ish else 30
        return AgentFinding(
            agent=self.name,
            summary=(
                "Production cluster - approval required for any mutation"
                if prod_ish
                else "Non-production cluster - approval still required by default"
            ),
            confidence=0.8,
            evidence=[
                "Autonomous mutation disabled unless explicitly enabled",
                f"cluster={event.cluster}",
            ],
            risk_score=risk,
            tags=["governance"],
        )


class CostAgent(BaseAgent):
    name = "cost-agent"

    async def inspect(self, event: InfrastructureEvent) -> AgentFinding:
        cost_relevant = event.event_type == EventType.cost or "cost" in event.message.lower()
        return AgentFinding(
            agent=self.name,
            summary=(
                "Potential cost impact detected"
                if cost_relevant
                else "No direct cost signal"
            ),
            confidence=0.65 if cost_relevant else 0.3,
            evidence=[event.message],
            risk_score=50 if cost_relevant else 10,
            tags=["cost"] if cost_relevant else [],
        )


class AgentRouter:
    def __init__(self, agents: list[BaseAgent] | None = None) -> None:
        self._agents: list[BaseAgent] = agents or [
            ObservabilityAgent(),
            SecurityAgent(),
            GovernanceAgent(),
            CostAgent(),
        ]

    @property
    def agent_names(self) -> list[str]:
        return [a.name for a in self._agents]

    async def run(self, event: InfrastructureEvent) -> list[AgentFinding]:
        # Run concurrently - cheap because each agent is a pure function today,
        # but the interface allows agents to call external systems later.
        return list(await asyncio.gather(*(agent.inspect(event) for agent in self._agents)))
