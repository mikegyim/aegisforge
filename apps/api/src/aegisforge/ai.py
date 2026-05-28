"""LLM-backed reasoning over inspection evidence.

This is the "brain" of AegisForge: it composes a structured prompt from the
event + agent findings + remediation plan, calls the configured LLM provider,
and returns an :class:`IncidentAnalysis`. Provider failures fall back to a
deterministic synthesis so the API never hard-fails on an LLM outage.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from .llm import LLMError, LLMProvider, MockProvider
from .models import (
    AgentFinding,
    EventType,
    IncidentAnalysis,
    InfrastructureEvent,
    RemediationPlan,
    SimilarIncident,
    SimulationResult,
)

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are AegisForge, an SRE-grade incident reasoning system.
You receive a structured cloud infrastructure event, findings from specialized
inspection agents, and a candidate remediation plan. Produce a concise,
production-quality analysis. Be precise. Do not invent facts."""


SCHEMA_HINT = (
    '{"root_cause_hypothesis": str, "executive_summary": str, '
    '"recommended_actions": [str], "confidence": float}'
)


def _render_user_prompt(
    event: InfrastructureEvent,
    findings: list[AgentFinding],
    plan: RemediationPlan,
    similar: list[SimilarIncident],
) -> str:
    parts = [
        f"EVENT id={event.event_id} type={event.event_type.value} "
        f"severity={event.severity.value} cluster={event.cluster} "
        f"namespace={event.namespace} workload={event.workload}",
        f"SIGNAL: {event.signal}",
        f"MESSAGE: {event.message}",
        "",
        "AGENT FINDINGS:",
    ]
    for f in findings:
        parts.append(
            f"- [{f.agent}] risk={f.risk_score} conf={f.confidence:.2f} "
            f"tags={','.join(f.tags) or '-'} :: {f.summary}"
        )
        for ev in f.evidence:
            parts.append(f"    evidence: {ev}")

    parts.append("")
    parts.append(f"CANDIDATE PLAN: {plan.title} (risk={plan.risk})")
    for a in plan.actions:
        parts.append(f"  - {a}")

    if similar:
        parts.append("")
        parts.append("HISTORICAL SIMILAR INCIDENTS:")
        for s in similar:
            parts.append(f"  - {s.event_id} ({s.cluster}/{s.signal}) sim={s.similarity:.2f}")

    return "\n".join(parts)


class ReasoningEngine:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider or MockProvider()

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    async def analyze(
        self,
        event: InfrastructureEvent,
        findings: list[AgentFinding],
        plan: RemediationPlan,
        simulation: SimulationResult,
        similar: list[SimilarIncident] | None = None,
    ) -> IncidentAnalysis:
        similar = similar or []
        user_prompt = _render_user_prompt(event, findings, plan, similar)

        response: dict[str, Any]
        try:
            response = await self._provider.complete_json(SYSTEM_PROMPT, user_prompt, SCHEMA_HINT)
        except LLMError as exc:
            log.warning("LLM call failed, using deterministic synthesis: %s", exc)
            response = self._fallback(event, findings, plan)

        root_cause = response.get("root_cause_hypothesis") or self._fallback_root_cause(event)
        summary = response.get("executive_summary") or self._fallback_summary(event, plan)

        # Apply LLM-recommended actions on top of the plan, deduped, preserving order.
        recommended = response.get("recommended_actions") or []
        if isinstance(recommended, list):
            seen = set(plan.actions)
            for action in recommended:
                if isinstance(action, str) and action not in seen:
                    plan.actions.append(action)
                    seen.add(action)

        return IncidentAnalysis(
            incident_id=str(uuid.uuid4()),
            event=event,
            findings=findings,
            root_cause_hypothesis=root_cause,
            remediation_plan=plan,
            simulation=simulation,
            executive_summary=summary,
            similar_incidents=similar,
            llm_provider=self._provider.name,
            llm_model=self._provider.model,
        )

    # ----- fallbacks (deterministic) ------------------------------------------
    def _fallback(
        self,
        event: InfrastructureEvent,
        findings: list[AgentFinding],
        plan: RemediationPlan,
    ) -> dict[str, Any]:
        return {
            "root_cause_hypothesis": self._fallback_root_cause(event),
            "executive_summary": self._fallback_summary(event, plan),
            "recommended_actions": [],
            "confidence": max((f.confidence for f in findings), default=0.5),
        }

    def _fallback_root_cause(self, event: InfrastructureEvent) -> str:
        if event.event_type == EventType.security:
            return f"Potential security anomaly: {event.signal} on {event.cluster}."
        return f"{event.signal} observed on {event.cluster} ({event.severity.value})."

    def _fallback_summary(self, event: InfrastructureEvent, plan: RemediationPlan) -> str:
        return (
            f"AegisForge detected a {event.severity.value} {event.event_type.value} "
            f"event on cluster {event.cluster}. Primary signal: {event.signal}. "
            f"Recommended plan: {plan.title}."
        )
