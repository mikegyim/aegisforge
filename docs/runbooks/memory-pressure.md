# Runbook: node memory pressure

**Symptoms.** Pods OOMKilled. Node `MemoryPressure` condition true.
Workload restart loops. p99 latency rises.

**AegisForge response.** The observability agent flags the event with the
`memory` tag, the planner emits a Deployment patch raising requests to 512Mi
and limits to 1Gi, and the simulator confirms workload-level blast radius.

**Human checklist.**

1. Confirm the PR diff is scoped to the affected workload only.
2. Verify the rollback plan is reflected in the prior values revision.
3. Watch `kube_pod_container_status_terminated_reason{reason="OOMKilled"}`
   for 15 minutes after merge.
4. If pressure recurs, escalate to capacity planning - the node pool needs
   to be larger, not the workload limits.

**Failure modes.**

- If the deployment lacks a PDB, rolling the workload may briefly drop
  capacity below the SLO floor. The chart ships a PDB by default.
- If memory pressure is cluster-wide, raising limits on one workload moves
  the problem rather than fixing it. Re-check across namespaces before merge.
