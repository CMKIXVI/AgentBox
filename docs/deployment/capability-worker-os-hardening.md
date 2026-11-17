# Capability worker OS hardening

The capability worker's spawned processes are **not a security sandbox by themselves**. A child runs as the worker OS identity and inherits its service cgroup, filesystem view, network access and process environment. The systemd unit in this directory supplies a hardened baseline for Linux deployments; it does not provide per-handler credentials or a per-handler network policy.

## Installation

1. Build and install AgentBox into `/opt/agentbox`, with its virtual environment at `/opt/agentbox/.venv`.
2. Create a dedicated unprivileged account and a private data directory:

   ```sh
   sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin agentbox-worker
   sudo install -d -o agentbox-worker -g agentbox-worker -m 0700 /var/lib/agentbox
   sudo install -d -o root -g root -m 0755 /etc/agentbox
   ```

3. Install `agentbox-capability-worker.service` into `/etc/systemd/system/`.
4. Create `/etc/agentbox/worker.env` containing only non-secret runtime settings. At minimum, point the worker at the shared durable-job database:

   ```ini
   AGENTBOX_DATABASE_PATH=/var/lib/agentbox/agentbox.sqlite3
   ```

   The API service and worker must use the same durable database and compatible schema. Ensure the API's database directory permissions permit the worker account to access it; do not broaden permissions beyond the required service accounts.
5. Reload and start:

   ```sh
   sudo systemctl daemon-reload
   sudo systemctl enable --now agentbox-capability-worker.service
   sudo systemctl status agentbox-capability-worker.service
   ```

## Controls supplied by the unit

- Dedicated non-login Unix identity; no Linux capabilities and no privilege escalation.
- Read-only system and application filesystems, with only the AgentBox data directory writable.
- Private temporary directory and devices; protected home, kernel, control-group and clock interfaces.
- Namespace creation and SUID/SGID transitions restricted.
- Worker and spawned children share service-level task, memory and CPU limits.
- Network address families are limited to Unix, IPv4 and IPv6 sockets.

The network setting is **not** an egress allowlist. Enforce destination-level egress rules outside systemd (host firewall, security group or controlled outbound proxy). Permit only the database and explicitly required provider endpoints.

## Credential boundary — critical

Do not place provider/API credentials, cloud credentials, signing keys or database passwords in `worker.env`, systemd environment directives, or the worker process environment. Python's spawned child inherits the worker environment. Therefore this unit does **not** isolate secrets between handlers.

The current capability runtime has no handler-scoped secret broker or per-handler OS identity. Until that exists, register only reviewed handlers that do not require ambient secrets; use an authenticated external service boundary where possible. Do not claim tenant-level or handler-level credential isolation. A future secret broker must authorize each secret request against the immutable capability identity and tenant, return short-lived scoped material over an explicit IPC channel, and avoid exposing credentials in environment variables, logs, job payloads or audit events.

## Deployment assumptions and limits

- Linux with a systemd version supporting the listed sandboxing directives.
- The worker and its child processes remain trusted application code. This is defense in depth, not a hostile-code sandbox.
- SQLite WAL/SHM files are created beside the database, so the data directory must remain writable.
- The service requires outbound network access for configured providers; enforce destination allowlists externally.
- Resource limits are service-wide, not per invocation. A noisy handler can consume the shared worker budget.
- Validate the unit against the target distribution and inspect `systemd-analyze security agentbox-capability-worker.service`; the score is advisory, not proof of security.

## Remaining production hardening

1. Handler-scoped secret broker and short-lived credentials.
2. Per-handler network egress policy and destination allowlist.
3. Per-invocation CPU, memory, process and file-descriptor quotas (not only service-wide limits).
4. A stronger isolation boundary for any code not fully trusted, such as a dedicated container/VM or microVM runtime with a separately managed identity.
5. Live deployment verification, including filesystem, process, network and credential-boundary tests.
## Capability secret broker contract

The worker exposes `CapabilityInvocationContext.resolve_secret(secret_ref, purpose)`. It constructs a broker request containing the authenticated job's tenant and subject, immutable capability ID/version and contract hash, plus the opaque reference and declared purpose. The handler cannot supply or override tenant, subject, capability identity or contract hash.

The default `DenyAllCapabilitySecretBroker` rejects every request. A deployment must replace the static `app.worker.CAPABILITY_SECRET_BROKER` with a reviewed, importable broker client (or inject one into `ExecutionJobWorker`); the implementation must independently authorize the exact tuple, return short-lived material, enforce expiry/revocation, and avoid logging values. Broker implementations are passed into spawned child processes and therefore must be safe to serialize and connect from that process. Do not implement a broker by reading ambient environment variables.

This change defines and tests the broker contract only. It does **not** ship a Vault/KMS/cloud-secret-manager adapter, transport authentication, secret rotation, revocation, per-handler identity, or a live secret store. Until a production broker adapter is deployed and verified, secret resolution remains unavailable and handlers must fail closed.


## Per-invocation resource limits

Each spawned capability child now applies POSIX resource limits before calling its
registered handler: CPU time is bounded to the declared wall-time budget plus a
one-second startup/teardown allowance; address space is capped at 1 GiB; individual
files at 16 MiB; open file descriptors at 64; and core dumps are disabled. The
parent process continues to enforce the independent wall-clock deadline, while
systemd cgroups continue to enforce aggregate worker limits.

These are fixed trusted-runtime defaults, not values supplied by a capability
contract or caller. They may need tuning for production workloads. They do not
limit network destinations, provide a per-invocation process-count boundary, or
isolate filesystem/network credentials. The child remains trusted application
code, not hostile-code sandboxing. The implementation fails closed on platforms
without POSIX resource-limit support.


## Optional outbound-proxy-only network boundary

For deployments with a separately managed, policy-enforcing HTTP(S) proxy, install
the optional drop-in at
`/etc/systemd/system/agentbox-capability-worker.service.d/egress-proxy.conf`:

```ini
[Service]
IPAddressDeny=any
IPAddressAllow=127.0.0.1/8
IPAddressAllow=::1/128
```

The repository supplies this as
`deploy/systemd/agentbox-capability-worker-egress-proxy.conf`. Create the drop-in
directory, copy the file, and configure the worker's non-secret `HTTP_PROXY` and
`HTTPS_PROXY` settings to point to the local proxy (for example,
`http://127.0.0.1:3128`). Do not add broad `NO_PROXY` entries: they bypass the
proxy for matching destinations. Then run `systemctl daemon-reload` and restart
the worker during a controlled deployment window.

This is an optional, fail-closed network boundary: direct IPv4/IPv6 destinations
from the worker and its children are denied; only loopback IP connections remain
available. The proxy must independently enforce hostname, resolved-IP, port,
scheme and redirect policies, including DNS resolution and protection against
private/link-local address access. Run the proxy as a separate service/identity
with its own egress firewall policy. A proxy that permits arbitrary CONNECT or
forwards arbitrary destinations defeats the control.

The drop-in does not filter Unix-domain sockets, distinguish loopback ports, or
protect against a compromised local proxy. Validate the effective policy and
proxy behavior on the target host before enabling it. Do not apply this drop-in
unless the proxy is already running and the required provider endpoints are
explicitly allowlisted; otherwise outbound provider calls will fail closed.
