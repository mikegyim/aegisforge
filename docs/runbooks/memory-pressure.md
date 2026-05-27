# Runbook: Node Memory Pressure

## Detection

Signals:

- Kubernetes NodeMemoryPressure
- OOMKilled pod events
- Prometheus memory saturation alerts

## Triage

```bash
kubectl top nodes
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe node <node>
kubectl get pods -A --field-selector=status.phase=Failed
```

## Remediation

- Increase workload memory requests and limits
- Move bursty CI workloads to dedicated node group
- Add cluster autoscaler or Karpenter
- Review memory leaks
