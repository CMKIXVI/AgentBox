import { signIn } from "@/auth";
import { oidcConfigured } from "@/auth";

export default function SignInPage() {
  if (!oidcConfigured) {
    return (
      <main className="shell">
        <section className="hero">
          <p className="eyebrow">AGENTBOX IDENTITY</p>
          <h1>Sign-in is not configured.</h1>
          <p className="intro">
            Configure the OIDC issuer, web client credentials, and AUTH_SECRET
            in the server environment before enabling authentication.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">AGENTBOX IDENTITY</p>
        <h1>Sign in to AgentBox.</h1>
        <p className="intro">
          Continue through your organization&apos;s configured identity provider.
        </p>
        <form
          action={async () => {
            "use server";
            await signIn("agentbox-oidc", { redirectTo: "/" });
          }}
        >
          <button className="signin-button" type="submit">
            Continue with your identity provider
          </button>
        </form>
      </section>
    </main>
  );
}
