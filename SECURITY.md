# Security policy

## Reporting a vulnerability

If you believe you have found a security vulnerability in AegisForge, please
**do not open a public issue**. Instead, email the maintainer at
`mikegyim@yahoo.com` with the subject `AegisForge security report`. Include:

- a description of the issue
- steps to reproduce
- any proof-of-concept or affected versions

I aim to respond within 72 hours and to ship a fix or mitigation within 14 days
of confirmation, depending on severity.

## Threat model

AegisForge is a control plane that proposes infrastructure changes. The most
important properties are:

1. **No autonomous mutation by default.** All remediation plans require human
   approval. `AEGIS_ENABLE_AUTONOMOUS_ACTIONS` is the only switch that changes
   this, and it is `false` by default.
2. **Defense in depth at the GitOps boundary.** Every proposed change is
   delivered as a draft pull request to a separate infrastructure repository.
   Merging - and therefore deployment - is the responsibility of a human
   reviewer.
3. **Policy pre-check.** The digital twin simulator mirrors the OPA policy and
   blocks plans that would be rejected at admission time.

## Hardening checklist applied in this repo

- Container runs as non-root with read-only root filesystem, dropped
  capabilities, and the runtime-default seccomp profile.
- Helm chart ships a NetworkPolicy default-deny for ingress/egress.
- API supports an optional `X-API-Key` and slowapi rate limiting.
- CI runs `ruff`, `bandit`, `trivy`, and `conftest verify`.
- Pod Security Standards `restricted` is enforced at the namespace level.

## Out of scope

Issues that require physical access, social engineering, or compromised CI
credentials. Issues in third-party dependencies should be reported upstream.
