# Digital twin notes

The twin is a small declarative graph (`digital_twin.yaml`) loaded at startup.
It captures the cluster topology that matters for blast-radius reasoning:

- which namespaces exist
- which deployments live in them
- replica counts, PDB presence, resource-limit presence
- the directed `serves` edges (callers of a downstream service)

The simulator uses the graph to:

1. classify blast radius (none / workload / namespace / cluster)
2. pre-check policy violations that mirror the OPA rules
3. score a deterministic risk integer the API can return on `/events`

For production deployments, the graph would be replaced by a live snapshot
fetched from the Kubernetes API and refreshed periodically. The interface is
the same; only the loader changes.
