import { auth, oidcConfigured, signOut } from "@/auth";
import Workspace from "./workspace";

export default async function Home() {
  const session = await auth();

  if (session) {
    return (
      <>
        <div className="session-bar">
          <span>{session.user?.email ?? "Authenticated AgentBox user"}</span>
          <form action={async () => {
            "use server";
            await signOut({ redirectTo: "/signin" });
          }}>
            <button className="signin-button" type="submit">Sign out</button>
          </form>
        </div>
        <Workspace />
      </>
    );
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="AgentBox home">
          <span className="brand-mark">A</span><span>AgentBox</span>
        </a>
        <a className="signin-link" href="/signin">
          {oidcConfigured ? "Sign in" : "Identity setup required"}
        </a>
      </header>
      <section className="hero">
        <p className="eyebrow">ONE PLATFORM · FIVE PILLARS</p>
        <h1>Build, operate, and evolve agents.</h1>
        <p className="intro">
          AgentBox brings AI intelligence, agent creation, application composition,
          execution, and platform governance into one environment.
        </p>
        <a className="signin-link hero-action" href="/signin">
          {oidcConfigured ? "Enter AgentBox" : "Configure identity"}
        </a>
      </section>
      <section className="workspace-grid">
        {[
          ["AI Intelligence", "Intent, context, cognition, verification, and memory."],
          ["Agent Factory", "Immutable agent manifests, versions, and lineage."],
          ["Application Factory", "Compose governed capabilities and workflows."],
          ["Execution Engine", "Run, observe, and recover bounded agent work."],
          ["Platform Foundation", "Identity, tenancy, authorization, audit, and persistence."],
        ].map(([title, description]) => (
          <article className="workspace-card" key={title}>
            <h3>{title}</h3><p>{description}</p>
          </article>
        ))}
      </section>
      <footer><span>AgentBox · Web Console</span><span>One backend authority · Two coordinated clients</span></footer>
    </main>
  );
}
