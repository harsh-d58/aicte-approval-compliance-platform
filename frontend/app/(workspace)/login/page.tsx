"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Icon, { type IconName } from "@/app/components/Icon";
import { roleNames, safeReturnTo } from "@/lib/portal/view-models";
import type { Role } from "@/lib/portal/types";
import { useDemo } from "@/app/portal-ui/DemoProvider";
import { useLive } from "@/app/portal-ui/LiveProvider";
import { Arrow, Brand } from "@/app/portal-ui/ui";
import s from "@/app/portal-ui/portal.module.css";

const icons: Record<Role, IconName> = {
  INSTITUTION: "institution",
  SCRUTINY: "search",
  REGIONAL: "map",
  EVC_COORDINATOR: "calendar",
  EVC_EXPERT: "user",
  COMPLIANCE: "shield",
  CENTRAL: "monitor",
  POLICY: "settings",
  AUDITOR: "document",
  SYSTEM: "settings",
};

const staticPersonas: { id: string; role: Role; name: string }[] = [
  { id: "user-institution", role: "INSTITUTION", name: "Ananya Rao" },
  { id: "user-scrutiny", role: "SCRUTINY", name: "Rohan Mehta" },
  { id: "user-regional", role: "REGIONAL", name: "Meera Desai" },
  { id: "user-coordinator", role: "EVC_COORDINATOR", name: "Kabir Shah" },
  { id: "user-expert-001", role: "EVC_EXPERT", name: "Aditi Sharma" },
  { id: "user-compliance", role: "COMPLIANCE", name: "Nisha Sen" },
  { id: "user-central", role: "CENTRAL", name: "Arjun Iyer" },
  { id: "user-policy", role: "POLICY", name: "Tara Menon" },
  { id: "user-auditor", role: "AUDITOR", name: "Dev Sethi" },
  { id: "user-system", role: "SYSTEM", name: "Isha Kapoor" },
];

export default function LoginPage() {
  const [authMode, setAuthMode] = useState<"demo" | "live">("demo");
  const { allData, error, signIn, reload, user } = useDemo();
  const [selected, setSelected] = useState("user-institution");
  const [submitting, setSubmitting] = useState(false);
  const [loginError, setLoginError] = useState("");
  const router = useRouter();

  const distinctPersonas = allData?.users.filter(
    (u, index, users) =>
      users.findIndex((other) => other.assignments[0]?.role === u.assignments[0]?.role) === index
  );
  const personas = distinctPersonas && distinctPersonas.length >= 10
    ? distinctPersonas.map(u => ({ id: u.id, role: u.assignments[0].role, name: u.displayName }))
    : staticPersonas;

  const selectedPersona = personas.find((p) => p.id === selected) ?? personas[0];

  async function enterDemo() {
    if (submitting) return;
    setSubmitting(true);
    try { await signIn(selectedPersona.id); } catch (cause) { setLoginError(cause instanceof Error ? cause.message : "Unable to open demo workspace."); setSubmitting(false); return; }
    const destination = safeReturnTo(new URLSearchParams(window.location.search).get("returnTo"));
    const userObj = allData?.users.find((u) => u.id === selectedPersona.id);
    router.push(
      userObj && userObj.assignments.length > 1
        ? `/portal/access?returnTo=${encodeURIComponent(destination)}`
        : destination
    );
  }

  return (
    <div className={s.authPage}>
      <header className={s.authHeader}>
        <Brand />
        <Link href="/" className={s.backLink}>
          <Arrow back />Back to home
        </Link>
      </header>

      <main id="main-content" className={s.authMain}>
        <section className={s.authIntro}>
          <span className={s.eyebrow}>ONE PLATFORM. EVERY STAGE.</span>
          <h1>
            A clearer path.<br />
            <span>A connected workspace.</span>
          </h1>
          <p>
            From your first submission to the final decision, bring every application,
            document and next step into focus.
          </p>
          <Image
            src="/footprint.png"
            alt="Connected digital services on desktop, tablet and mobile"
            width={560}
            height={400}
            className={s.authIllustration}
            unoptimized
          />
          <span className={s.authFeature}>
            <Icon name="shield" size={14} />Scoped access
          </span>
          <span className={s.authFeature}>
            <Icon name="check" size={14} />Traceable decisions
          </span>
        </section>

        <section className={s.authCard} aria-labelledby="signin-title">
          <span className={s.eyebrow}>AICTE STATUTORY PORTAL</span>
          <h2 id="signin-title">Choose your workspace.</h2>
          <p>Select any of the 10 demonstration roles or connect with live database credentials.</p>

          {/* Mode Switcher Tabs */}
          <div
            role="tablist"
            aria-label="Authentication mode"
            style={{
              display: "flex",
              gap: "6px",
              background: "rgba(0,0,0,0.05)",
              padding: "4px",
              borderRadius: "10px",
              margin: "18px 0 16px",
            }}
          >
            <button
              type="button"
              role="tab"
              aria-selected={authMode === "demo"}
              onClick={() => setAuthMode("demo")}
              style={{
                flex: 1,
                padding: "8px 12px",
                fontSize: "12px",
                fontWeight: 600,
                border: "none",
                borderRadius: "7px",
                cursor: "pointer",
                transition: "all 0.15s ease",
                background: authMode === "demo" ? "#ffffff" : "transparent",
                color: authMode === "demo" ? "#96502c" : "#64748b",
                boxShadow: authMode === "demo" ? "0 2px 8px rgba(0,0,0,0.08)" : "none",
              }}
            >
              👥 10 Role Personas (Instant)
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={authMode === "live"}
              onClick={() => setAuthMode("live")}
              style={{
                flex: 1,
                padding: "8px 12px",
                fontSize: "12px",
                fontWeight: 600,
                border: "none",
                borderRadius: "7px",
                cursor: "pointer",
                transition: "all 0.15s ease",
                background: authMode === "live" ? "#ffffff" : "transparent",
                color: authMode === "live" ? "#96502c" : "#64748b",
                boxShadow: authMode === "live" ? "0 2px 8px rgba(0,0,0,0.08)" : "none",
              }}
            >
              🔐 Live Database (PostgreSQL)
            </button>
          </div>

          {authMode === "demo" ? (
            <>
              <div className={s.authDemoLabel}>
                <span>EXPLORE AS (10 STATUTORY ROLES)</span>
                <span className={s.demoChip}>1-Click Access</span>
              </div>

              {(error || loginError) ? (
                <div role="alert">
                  <p>{error || loginError}</p>
                  <button onClick={() => { setLoginError(""); reload(); }} className={s.secondaryButton}>
                    Try again
                  </button>
                </div>
              ) : (
                <>
                  <div className={s.roleGrid} role="group" aria-label="10 Demonstration roles">
                    {personas.map((person) => {
                      const role = person.role;
                      return (
                        <button
                          type="button"
                          key={person.id}
                          className={s.roleButton}
                          aria-pressed={selected === person.id}
                          onClick={() => setSelected(person.id)}
                        >
                          <Icon name={icons[role]} size={17} />
                          <span>{roleNames[role]}</span>
                        </button>
                      );
                    })}
                  </div>

                  {selectedPersona && (
                    <div className={s.selectedUser}>
                      <span className={s.avatar}>
                        {selectedPersona.name
                          .split(" ")
                          .map((n) => n[0])
                          .join("")}
                      </span>
                      <span>
                        <strong>{selectedPersona.name}</strong>
                        <small>
                          {roleNames[selectedPersona.role]} · Instant sign-in (No password)
                        </small>
                      </span>
                    </div>
                  )}

                  <button
                    type="button"
                    className={s.primaryButton}
                    disabled={!selectedPersona || submitting}
                    onClick={enterDemo}
                  >
                    {submitting ? "Opening your workspace…" : "Enter demonstration portal"}
                    <Arrow />
                  </button>

                  {user && (
                    <Link className={s.textLink} href="/portal">
                      Continue as {user.displayName}
                      <Arrow />
                    </Link>
                  )}
                </>
              )}

              <p className={s.authDisclaimer}>
                Full functional prototype with all 10 role-based workflows and Power-BI analytics.<br />
                Your actions are saved to the shared prototype database.
              </p>
            </>
          ) : (
            <LiveLoginForm />
          )}

          <div className={s.authDivider} />
          <div className={s.ssoNote}>
            <Icon name="shield" size={17} />
            <span>
              Demo rules are illustrative. Access is checked by the server for each role and scope.
            </span>
          </div>
        </section>
      </main>

      <footer className={s.authFooter}>
        <span>AICTE Approval & Compliance Platform</span>
        <span>Prototype · Smart India Hackathon (SIH)</span>
      </footer>
    </div>
  );
}

function LiveLoginForm() {
  const { configured, identity, loading, signIn } = useLive();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signIn(email, password);
      const requested = new URLSearchParams(window.location.search).get("returnTo");
      router.replace(requested?.startsWith("/portal") && !requested.startsWith("//") ? requested : "/portal");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Sign-in failed. Check database credentials.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}>
      <div style={{ fontSize: "11px", color: "#475569", background: "#f8fafc", padding: "10px 12px", borderRadius: "8px", border: "1px solid #e2e8f0", lineHeight: "1.6" }}>
        <strong>Live PostgreSQL & Supabase Engine</strong>
        <p style={{ margin: "3px 0 0", color: "#64748b" }}>
          Authenticates against the live backend with Row-Level Security (RLS) policies.
        </p>
      </div>

      {!configured && (
        <p role="alert" style={{ fontSize: "11px", color: "#b45309", background: "#fef3c7", padding: "8px 10px", borderRadius: "6px" }}>
          Live sign-in requires Supabase URL and key configuration.
        </p>
      )}

      {error && (
        <p role="alert" style={{ fontSize: "11px", color: "#b91c1c", background: "#fee2e2", padding: "8px 10px", borderRadius: "6px" }}>
          {error}
        </p>
      )}

      {identity && (
        <p style={{ fontSize: "12px", color: "#15803d", margin: "4px 0" }}>
          Signed in as <strong>{identity.user.display_name}</strong>.{" "}
          <Link href="/portal" style={{ textDecoration: "underline", fontWeight: 600 }}>Enter workspace →</Link>
        </p>
      )}

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
        Email address
        <input
          type="email"
          autoComplete="username"
          required
          placeholder="officer@aicte.gov.in"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={!configured || busy}
          className={s.input}
        />
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px", fontWeight: 600, color: "#475569" }}>
        Password
        <input
          type="password"
          autoComplete="current-password"
          required
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={!configured || busy}
          className={s.input}
        />
      </label>

      <button
        type="submit"
        className={s.primaryButton}
        disabled={!configured || loading || busy}
        style={{ width: "100%", marginTop: "6px" }}
      >
        {busy ? "Authenticating with database…" : "Sign in to Live Database"}
      </button>
    </form>
  );
}
