export type AccessTokenProvider = () => Promise<string | null>;

export type AgentVersionRecord = {
  agent_id: string;
  version: string;
  content_hash: string;
  manifest: Record<string, unknown>;
  parent_artifact_id: string | null;
  created_at: string;
  artifact_id: string;
};

export type AgentVersionList = {
  agent_id: string;
  items: AgentVersionRecord[];
  limit: number;
  offset: number;
};

export class AgentBoxApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail: unknown,
  ) {
    super(message);
    this.name = "AgentBoxApiError";
  }
}

export class AgentBoxApiClient {
  private readonly baseUrl: string;

  constructor(
    baseUrl: string,
    private readonly accessTokenProvider: AccessTokenProvider,
    private readonly fetcher: typeof fetch = fetch,
  ) {
    const parsed = new URL(baseUrl);
    if (parsed.protocol !== "https:" && parsed.hostname !== "localhost" && parsed.hostname !== "127.0.0.1") {
      throw new Error("AgentBox API must use HTTPS outside localhost development");
    }
    this.baseUrl = parsed.toString().replace(/\/$/, "");
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
    authenticated = true,
  ): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body !== undefined) headers.set("Content-Type", "application/json");

    if (authenticated) {
      const token = await this.accessTokenProvider();
      if (!token) throw new AgentBoxApiError("An authenticated session is required", 401, null);
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await this.fetcher(`${this.baseUrl}${path}`, {
      ...init,
      headers,
      credentials: "omit",
    });
    if (!response.ok) {
      let detail: unknown = null;
      try { detail = await response.json(); } catch { detail = await response.text(); }
      throw new AgentBoxApiError(`AgentBox API request failed (${response.status})`, response.status, detail);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  health(): Promise<{ status: string; service: string }> {
    return this.request("/health", {}, false);
  }

  listAgentVersions(agentId: string, limit = 50, offset = 0): Promise<AgentVersionList> {
    return this.request(
      `/v1/agents/${encodeURIComponent(agentId)}/versions?limit=${limit}&offset=${offset}`,
    );
  }

  getAgentVersion(agentId: string, version: string): Promise<AgentVersionRecord> {
    return this.request(
      `/v1/agents/${encodeURIComponent(agentId)}/versions/${encodeURIComponent(version)}`,
    );
  }

  createAgent(manifest: Record<string, unknown>): Promise<AgentVersionRecord & { created: boolean }> {
    return this.request("/v1/agents", { method: "POST", body: JSON.stringify({ manifest }) });
  }

  getExecution(executionId: string): Promise<Record<string, unknown>> {
    return this.request(`/v1/executions/${encodeURIComponent(executionId)}`);
  }
}
