from abc import ABC, abstractmethod

from .models import InfrastructureEvent, AgentFinding, EventType


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def inspect(self, event: InfrastructureEvent) -> AgentFinding:
        raise NotImplementedError


class ObservabilityAgent(BaseAgent):
    name = "observability-agent"

    async def inspect(self, event: InfrastructureEvent) -> AgentFinding:
        risk = 85 if event.severity == "critical" else 55
        return AgentFinding(
            agent=self.name,
            summary=f"Observed infrastructure signal: {event.signal}",
            confidence=0.82,
            evidence=[
                event.message,
                f"cluster={event.cluster}",
                f"workload={event.workload or 'unknown'}",
            ],
            risk_score=risk,
        )


class SecurityAgent(BaseAgent):
    name = "security-agent"

    async def inspect(self, event: InfrastructureEvent) -> AgentFinding:
        suspicious = event.event_type == EventType.security
        return AgentFinding(
            agent=self.name,
            summary="Security anomaly detected" if suspicious else "No direct security indicator",
            confidence=0.76 if suspicious else 0.42,
            evidence=[event.message],
            risk_score=90 if suspicious else 20,
        )


class GovernanceAgent(BaseAgent):
    name = "governance-agent"

    async def inspect(self, event: InfrastructureEvent) -> AgentFinding:
        return AgentFinding(
            agent=self.name,
            summary="Policy review completed",
            confidence=0.7,
            evidence=["Autonomous mutation is disabled unless approval is enabled"],
            risk_score=45,
        )


class AgentRouter:
    def __init__(self) -> None:
        self._agents: list[BaseAgent] = [
            ObservabilityAgent(),
            SecurityAgent(),
            GovernanceAgent(),
        ]

    async def run(self, event: InfrastructureEvent) -> list[AgentFinding]:
        return [await agent.inspect(event) for agent in self._agents]
