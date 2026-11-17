import { auth, oidcConfigured, signOut } from "@/auth";

const workspaces = [
  {
    title: "Agent Studio",
    description: "Create agents, inspect immutable versions, and manage configuration.",
    status: "Foundation",
  },
  {
    title: "Execution",
    description: "Inspect execution state, traces, and operational outcomes.",
    status: "Foundation",
  },
  {
    title: "Evaluation",
    description: "Manage evaluation profiles, benchmark evidence, and comparisons.",
    status: "Planned",
  },
  {
    title: "Evolution",
    description: "Review candidate lineage, experiments, gates, and approvals.",
    status: "Planned",
  },
];

export default async function Home() {
  const session = await auth();

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="AgentBox home">
          <span className="brand-mark">A</span>
          <span>AgentBox</span>
        </a>
        <div className="environment">
          {session?.user?.email ?? "Platform workspace · Preview"}
          {session ? (
            <form
              action={async () => {
                "use server";
                await signOut({ redirectTo: "/signin" });
              }}
            >
              <button className="signin-button" type="submit">Sign out</button>
            </form>
          ) : (
            <a className="signin-link" href="/signin">
              {oidcConfigured ? "Sign in" : "Identity setup required"}
            </a>
          )}
        </div>
      </header>

      <section className="hero">
        <p className="eyebrow">ONE PLATFORM · TWO CLIENTS</p>
        <h1>Build, operate, and evolve agents.</h1>
        <p className="intro">
          AgentBox brings agent creation, execution, evaluation, and governed
          improvement into one platform.
        </p>
      </section>

      <section aria-labelledby="workspace-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">WORKSPACES</p>
            <h2 id="workspace-heading">Your platform</h2>
          </div>
          <span className="count">04 areas</span>
        </div>
        <div className="workspace-grid">
          {workspaces.map((workspace) => (
            <article className="workspace-card" key={workspace.title}>
              <div className="card-topline">
                <span className="card-dot" aria-hidden="true" />
                <span className="card-status">{workspace.status}</span>
              </div>
              <h3>{workspace.title}</h3>
              <p>{workspace.description}</p>
            </article>
          ))}
        </div>
      </section>

      <footer>
        <span>AgentBox · Web Console</span>
        <span>
          {session
            ? "Authenticated web session · API operations are routed server-side."
            : "Preview mode · Sign in to establish an authenticated session."}
        </span>
      </footer>
    </main>
  );
}
