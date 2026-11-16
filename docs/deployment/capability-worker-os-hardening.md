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

The default `DenyAllCapabilitySecretBroker` rejects every request. A deployment must inject an authenticated broker implementation into `ExecutionJobWorker`; the implementation must independently authorize the exact tuple, return short-lived material, enforce expiry/revocation, and avoid logging values. Broker implementations are passed into spawned child processes and therefore must be safe to serialize and connect from that process. Do not implement a broker by reading ambient environment variables.

This change defines and tests the broker contract only. It does **not** ship a Vault/KMS/cloud-secret-manager adapter, transport authentication, secret rotation, revocation, per-handler identity, or a live secret store. Until a production broker adapter is deployed and verified, secret resolution remains unavailable and handlers must fail closed.
