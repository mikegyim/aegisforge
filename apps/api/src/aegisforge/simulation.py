from .models import RemediationPlan


class DigitalTwinSimulator:
    async def simulate(self, plan: RemediationPlan) -> dict[str, object]:
        risky_terms = ["scale suspicious workload to zero", "delete", "remove"]
        risk_detected = any(
            term in action.lower()
            for action in plan.actions
            for term in risky_terms
        )

        return {
            "simulation_status": "passed_with_approval_required" if risk_detected else "passed",
            "estimated_blast_radius": "namespace-level" if risk_detected else "workload-level",
            "safe_to_auto_apply": False,
            "notes": [
                "GitOps approval required before production mutation",
                "Simulation engine currently uses deterministic rule evaluation",
            ],
        }
