# AgentBox sandbox runtime foundation

## Status

This is the first executable isolation adapter, not a production certification. It
adds a Docker CLI runner that requires the gVisor `runsc` runtime and fails closed
when the configured image or isolation runtime is unavailable. The adapter is not
yet connected to the public execution API, candidate evaluator, or autonomous
controller.

## Security boundary

The Docker daemon, host kernel, gVisor installation, image registry, and host
operator remain trusted infrastructure. gVisor adds a userspace-kernel boundary
between workload processes and the host kernel; this design does not claim VM-grade
isolation or protection from a compromised daemon/host.

## Enforced invocation policy

- Exact allowlist of immutable OCI images pinned by SHA-256 digest.
- Mandatory `runsc`; no fallback to `runc` or the default runtime.
- No network, IPC namespace sharing, host mounts, bind mounts, or volume mounts.
- Read-only container root filesystem; bounded writable tmpfs only.
- Non-root UID/GID, all Linux capabilities dropped, no-new-privileges.
- CPU, memory, swap, process-count, file-descriptor, wall-clock, stdin, and combined
  stdout/stderr limits.
- Core dumps disabled; container logging disabled; image pull disabled at runtime.
- Minimal Docker CLI environment allowlist; no arbitrary workload environment.
- No shell interpolation: arguments are passed as an argv vector.

## Operational prerequisites

1. Install and configure Docker Engine with gVisor `runsc` registered as a runtime.
2. Build, scan, sign, and approve runner images; record immutable digests in the
   deployment allowlist.
3. Run the daemon on dedicated worker hosts with no ambient cloud credentials.
4. Apply host-level firewall, kernel patching, daemon socket protection, disk quotas,
   worker concurrency limits, and workload queue controls.
5. Validate gVisor compatibility and the exact Docker/gVisor versions in deployment.
6. Exercise timeout cleanup, daemon failure, worker restart, and output-flood cases.
7. For hostile multi-tenant or high-assurance workloads, evaluate a VM boundary
   (for example Kata Containers or dedicated microVM workers) in addition to this
   adapter; do not weaken the mandatory runtime as a workaround.

## Explicit limitations

- The adapter is not wired into `ExecutionService` or any HTTP route.
- No generated agent code is currently submitted to this runner.
- No real workload image has been approved or deployed by this change.
- Docker daemon isolation, host-level quotas, queue admission, concurrency, audit
  correlation, and operational recovery need deployment evidence.
- A container runtime is not a substitute for authorization, tool policy, secrets
  isolation, output validation, or human approval.
- CI validates policy construction and request validation; it does not execute a
  live gVisor workload.

## Acceptance gates before integration

- A dedicated worker deployment with pinned Docker and gVisor versions.
- End-to-end tests proving network isolation, filesystem isolation, resource caps,
  timeout cleanup, and output limits against a live worker.
- Tenant-authorized job submission and immutable execution/audit linkage.
- Queue admission, bounded concurrency, cancellation, restart recovery, and metrics.
- Security review of daemon access, image provenance, host hardening, and escape risk.
