"""Digital twin simulator.

Models the cluster as a small graph (nodes, namespaces, deployments, services)
and uses it to estimate the blast radius of a proposed :class:`RemediationPlan`.
The default graph is loaded from ``simulation/digital_twin.yaml`` so it can be
edited without touching code; callers may also inject a custom graph for tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .models import RemediationPlan, SimulationResult

log = logging.getLogger(__name__)


DEFAULT_GRAPH_PATH = Path(__file__).resolve().parents[3] / "simulation" / "digital_twin.yaml"


@dataclass
class Deployment:
    name: str
    namespace: str
    replicas: int = 1
    has_pdb: bool = False
    has_resource_limits: bool = False
    serves: list[str] = field(default_factory=list)  # downstream service names


@dataclass
class ClusterGraph:
    cluster: str
    namespaces: list[str]
    deployments: list[Deployment]

    @classmethod
    def from_yaml(cls, path: Path) -> ClusterGraph:
        if not path.exists():
            return cls.default()
        data = yaml.safe_load(path.read_text())
        return cls(
            cluster=data.get("cluster", "dev-us-east-1"),
            namespaces=data.get("namespaces", ["default"]),
            deployments=[Deployment(**d) for d in data.get("deployments", [])],
        )

    @classmethod
    def default(cls) -> ClusterGraph:
        return cls(
            cluster="dev-us-east-1",
            namespaces=["default", "ci", "platform"],
            deployments=[
                Deployment(
                    name="gitlab-runner",
                    namespace="ci",
                    replicas=3,
                    has_pdb=False,
                    has_resource_limits=False,
                    serves=[],
                ),
                Deployment(
                    name="api-gateway",
                    namespace="platform",
                    replicas=2,
                    has_pdb=True,
                    has_resource_limits=True,
                    serves=["auth", "billing"],
                ),
                Deployment(
                    name="auth",
                    namespace="platform",
                    replicas=2,
                    has_pdb=True,
                    has_resource_limits=True,
                    serves=[],
                ),
            ],
        )

    def find(self, name: str | None, namespace: str | None) -> Deployment | None:
        if not name:
            return None
        for d in self.deployments:
            if d.name == name and (namespace is None or d.namespace == namespace):
                return d
        return None


_HIGH_RISK_TERMS = (
    "scale",
    "delete",
    "remove",
    "drop",
    "drain",
    "evict",
    "rollback to",
    "force",
)
_MUTATION_TERMS = (
    "restart",
    "roll",
    "apply",
    "raise",
    "lower",
    "increase",
    "decrease",
    "quarantine",
    "isolate",
    "patch",
)


class DigitalTwinSimulator:
    def __init__(self, graph: ClusterGraph | None = None) -> None:
        self._graph = graph or ClusterGraph.from_yaml(DEFAULT_GRAPH_PATH)

    @property
    def graph(self) -> ClusterGraph:
        return self._graph

    async def simulate(
        self,
        plan: RemediationPlan,
        *,
        cluster: str | None = None,
        namespace: str | None = None,
        workload: str | None = None,
    ) -> SimulationResult:
        actions_lower = [a.lower() for a in plan.actions]
        joined = " | ".join(actions_lower)

        high_risk = any(term in joined for term in _HIGH_RISK_TERMS)
        mutation = any(term in joined for term in _MUTATION_TERMS)

        target = self._graph.find(workload, namespace)
        affected: list[str] = []
        if target is not None:
            affected.append(f"{target.namespace}/{target.name}")
            # downstream callers - reverse map
            for d in self._graph.deployments:
                if target.name in d.serves:
                    affected.append(f"{d.namespace}/{d.name}")

        # Blast radius classification
        if high_risk and target and not target.has_pdb:
            radius = "namespace-level"
        elif high_risk:
            radius = "workload-level (PDB present)"
        elif mutation:
            radius = "workload-level"
        else:
            radius = "none (read-only)"

        # Policy violations - cheap pre-check that mirrors the OPA policy
        policy_violations: list[str] = []
        patch = plan.gitops_patch or {}
        if patch.get("kind") == "Deployment":
            spec = patch.get("spec", {}).get("template", {}).get("spec", {})
            for c in spec.get("containers", []) or []:
                limits = (c.get("resources") or {}).get("limits") or {}
                if not limits.get("memory"):
                    policy_violations.append(
                        f"container {c.get('name')} must declare memory limit"
                    )

        # Risk score
        risk = 10
        if mutation:
            risk += 30
        if high_risk:
            risk += 30
        if policy_violations:
            risk += 30
        if target is None and (mutation or high_risk):
            # mutating an unknown workload is itself risky
            risk += 10
        risk = min(risk, 100)

        if policy_violations:
            status = "blocked"
        elif high_risk or mutation:
            status = "passed_with_approval_required"
        else:
            status = "passed"

        safe_to_auto_apply = (
            status == "passed"
            and risk < 30
            and not policy_violations
            and plan.risk == "low"
        )

        notes = [
            f"cluster_graph: {self._graph.cluster}",
            f"high_risk_terms_detected: {high_risk}",
            f"mutation_detected: {mutation}",
        ]
        if cluster and cluster != self._graph.cluster:
            notes.append(
                f"warning: event cluster '{cluster}' does not match digital twin "
                f"'{self._graph.cluster}'"
            )

        return SimulationResult(
            status=status,
            estimated_blast_radius=radius,
            affected_resources=affected,
            policy_violations=policy_violations,
            risk_score=risk,
            safe_to_auto_apply=safe_to_auto_apply,
            notes=notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster": self._graph.cluster,
            "namespaces": self._graph.namespaces,
            "deployments": [
                {
                    "name": d.name,
                    "namespace": d.namespace,
                    "replicas": d.replicas,
                    "has_pdb": d.has_pdb,
                    "has_resource_limits": d.has_resource_limits,
                    "serves": d.serves,
                }
                for d in self._graph.deployments
            ],
        }
