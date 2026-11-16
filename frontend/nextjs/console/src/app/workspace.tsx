"use client";

import { useMemo, useState } from "react";
import {
  AgentBoxApiError,
  AgentBoxBffClient,
  type AgentVersionRecord,
} from "@/lib/agentbox-api";

const api = new AgentBoxBffClient();

const starterManifest = {
  schema_version: "1.0.0",
  agent_id: "sample-support-agent",
  version: "1.0.0",
  name: "Support assistant",
  description: "A governed support assistant agent.",
  purpose: "Answer support questions using approved knowledge and tools.",
  behavior: {
    objective: "Provide accurate, concise support answers and ask for clarification when needed.",
    instructions_ref: "agentbox://instructions/support-assistant",
    max_steps: 8,
    timeout_seconds: 120,
  },
  model_binding: {
    provider_id: "openai-compatible",
    model_id: "gpt-4o-mini",
  },
  tools: [],
  permissions: { tool_scopes: [], data_scopes: [] },
  provenance: {
    origin: "authored",
    created_at: "2026-11-16T00:00:00Z",
  },
  runtime_targets: ["server"],
  tags: ["starter"],
};

function errorMessage(error: unknown): string {
  if (error instanceof AgentBoxApiError) {
    const detail = error.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "detail" in detail) {
      return String((detail as { detail: unknown }).detail);
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "Unexpected error";
}

function JsonPanel({ value }: { value: unknown }) {
  return <pre className="json-panel">{JSON.stringify(value, null, 2)}</pre>;
}

export default function Workspace() {
  const [manifestText, setManifestText] = useState(
    JSON.stringify(starterManifest, null, 2),
  );
  const [agentId, setAgentId] = useState("");
  const [versions, setVersions] = useState<AgentVersionRecord[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<AgentVersionRecord | null>(null);
  const [executionId, setExecutionId] = useState("");
  const [execution, setExecution] = useState<Record<string, unknown> | null>(null);
  const [created, setCreated] = useState<AgentVersionRecord | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  const versionCount = useMemo(() => versions.length, [versions]);

  async function createAgent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("create");
    setNotice(null);
    setCreated(null);
    try {
      const manifest = JSON.parse(manifestText) as Record<string, unknown>;
      const result = await api.createAgent(manifest);
      setCreated(result);
      setAgentId(result.agent_id);
      setNotice({ kind: "success", text: result.created ? "Agent version registered." : "This immutable agent version already exists." });
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof SyntaxError ? "Manifest must be valid JSON." : errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function loadVersions(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("versions");
    setNotice(null);
    setSelectedVersion(null);
    try {
      const result = await api.listAgentVersions(agentId.trim());
      setVersions(result.items);
      setNotice({ kind: "success", text: `Loaded ${result.items.length} version(s) for ${result.agent_id}.` });
    } catch (error) {
      setVersions([]);
      setNotice({ kind: "error", text: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function loadVersion(version: string) {
    setBusy("version");
    setNotice(null);
    try {
      const result = await api.getAgentVersion(agentId.trim(), version);
      setSelectedVersion(result);
    } catch (error) {
      setNotice({ kind: "error", text: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function loadExecution(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("execution");
    setNotice(null);
    setExecution(null);
    try {
      setExecution(await api.getExecution(executionId.trim()));
    } catch (error) {
      setNotice({ kind: "error", text: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="AgentBox home">
          <span className="brand-mark">A</span><span>AgentBox</span>
        </a>
        <p className="side-label">PLATFORM</p>
        <nav className="side-nav" aria-label="Workspace sections">
          <a className="active" href="#overview">Overview</a>
          <a href="#agent-studio">Agent Studio</a>
          <a href="#execution">Execution</a>
          <a href="#governance">Governance</a>
        </nav>
        <div className="sidebar-foot">
          <span className="status-pip" /> API-backed workspace
          <small>Backend remains the authority for access and policy.</small>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div><span className="crumb">WORKSPACE</span><strong>Overview</strong></div>
          <span className="environment-pill">AgentBox platform</span>
        </header>

        <section className="welcome" id="overview">
          <div>
            <p className="eyebrow">AGENT OPERATING ENVIRONMENT</p>
            <h1>Build. Run. Learn. Govern.</h1>
            <p className="intro">One platform for agent intelligence, agent creation, application composition, execution, and platform governance.</p>
          </div>
          <div className="welcome-mark" aria-hidden="true">A<span>•</span></div>
        </section>

        {notice && (
          <div className={`notice ${notice.kind}`} role="status">{notice.text}</div>
        )}

        <section className="metric-grid" aria-label="Platform capabilities">
          <article className="metric-card"><span className="metric-icon">01</span><strong>AI Intelligence</strong><p>Context, cognition, verification, and memory.</p><span className="metric-state">Runtime foundation</span></article>
          <article className="metric-card"><span className="metric-icon">02</span><strong>Agent Factory</strong><p>Immutable manifests, versions, and lineage.</p><span className="metric-state">API connected</span></article>
          <article className="metric-card"><span className="metric-icon">03</span><strong>Application Factory</strong><p>Compose governed capabilities and workflows.</p><span className="metric-state planned">In progress</span></article>
          <article className="metric-card"><span className="metric-icon">04</span><strong>Execution Engine</strong><p>Inspect execution records and outcomes.</p><span className="metric-state">API connected</span></article>
          <article className="metric-card"><span className="metric-icon">05</span><strong>Platform Foundation</strong><p>Identity, tenancy, policy, audit, and data.</p><span className="metric-state">API connected</span></article>
        </section>

        <section className="content-section" id="agent-studio">
          <div className="section-heading">
            <div><p className="eyebrow">AGENT FACTORY</p><h2>Agent Studio</h2><p>Create a versioned agent or inspect an existing agent's immutable versions.</p></div>
            <span className="section-count">{versionCount} versions loaded</span>
          </div>
          <div className="two-column">
            <article className="surface-card">
              <div className="card-heading"><div><span className="card-kicker">NEW ARTIFACT</span><h3>Register agent version</h3></div><span className="card-symbol">＋</span></div>
              <form onSubmit={createAgent} className="stack-form">
                <label htmlFor="manifest">Agent manifest · JSON</label>
                <textarea id="manifest" value={manifestText} onChange={(event) => setManifestText(event.target.value)} rows={19} spellCheck={false} />
                <p className="helper">Uses the canonical AgentBox manifest contract. Secrets must be referenced, never embedded.</p>
                <button className="primary-button" type="submit" disabled={busy !== null}>{busy === "create" ? "Registering…" : "Register immutable version"}</button>
              </form>
              {created && <div className="result-card"><strong>{created.agent_id} · v{created.version}</strong><small>Artifact: {created.artifact_id}</small><small>SHA-256: {created.content_hash}</small></div>}
            </article>

            <article className="surface-card">
              <div className="card-heading"><div><span className="card-kicker">VERSION HISTORY</span><h3>Inspect an agent</h3></div><span className="card-symbol">↗</span></div>
              <form onSubmit={loadVersions} className="stack-form">
                <label htmlFor="agent-id">Agent ID</label>
                <input id="agent-id" value={agentId} onChange={(event) => setAgentId(event.target.value)} placeholder="e.g. sample-support-agent" required />
                <button className="secondary-button" type="submit" disabled={busy !== null || !agentId.trim()}>{busy === "versions" ? "Loading…" : "Load versions"}</button>
              </form>
              {versions.length > 0 ? (
                <div className="version-list">
                  {versions.map((item) => <button className={selectedVersion?.version === item.version ? "version-row selected" : "version-row"} key={item.artifact_id} onClick={() => void loadVersion(item.version)} type="button"><span><strong>v{item.version}</strong><small>{new Date(item.created_at).toLocaleString()}</small></span><span className="version-arrow">→</span></button>)}
                </div>
              ) : <p className="empty-state">No versions loaded. Enter an agent ID to query the tenant-scoped registry.</p>}
              {selectedVersion && <div className="detail-block"><div className="detail-title">Version manifest</div><JsonPanel value={selectedVersion.manifest} /></div>}
            </article>
          </div>
        </section>

        <section className="content-section" id="execution">
          <div className="section-heading">
            <div><p className="eyebrow">EXECUTION ENGINE</p><h2>Execution inspector</h2><p>Retrieve a real execution record using its identifier.</p></div>
          </div>
          <article className="surface-card execution-card">
            <form onSubmit={loadExecution} className="inline-form">
              <div className="field-grow"><label htmlFor="execution-id">Execution ID</label><input id="execution-id" value={executionId} onChange={(event) => setExecutionId(event.target.value)} placeholder="Paste an execution ID" required /></div>
              <button className="primary-button" type="submit" disabled={busy !== null || !executionId.trim()}>{busy === "execution" ? "Loading…" : "Inspect execution"}</button>
            </form>
            {execution ? <JsonPanel value={execution} /> : <p className="empty-state">Execution records appear here after a successful API lookup. No simulated data is shown.</p>}
          </article>
        </section>

        <section className="content-section" id="governance">
          <div className="section-heading"><div><p className="eyebrow">GOVERNANCE</p><h2>Trust boundaries</h2><p>These controls remain enforced by the backend, regardless of what the UI displays.</p></div></div>
          <div className="governance-grid">
            <div className="governance-item"><strong>Identity & tenancy</strong><p>OIDC identity and tenant context are verified server-side.</p></div>
            <div className="governance-item"><strong>Authorization</strong><p>Capabilities and resource ownership are decided by backend policy.</p></div>
            <div className="governance-item"><strong>Evidence & audit</strong><p>UI actions do not bypass evidence review or append-only audit.</p></div>
          </div>
        </section>
        <footer className="workspace-footer"><span>AgentBox · Web Console</span><span>Contract-driven · Tenant-scoped · Backend-governed</span></footer>
      </main>
    </div>
  );
}
