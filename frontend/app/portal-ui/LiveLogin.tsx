"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useLive } from "./LiveProvider";
import s from "./live.module.css";

export default function LiveLogin() {
  const { configured, identity, loading, signIn } = useLive();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      await signIn(email, password);
      const requested = new URLSearchParams(window.location.search).get("returnTo");
      router.replace(requested?.startsWith("/portal") && !requested.startsWith("//") ? requested : "/portal");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Sign-in failed.");
    } finally { setBusy(false); }
  }
  return <div className={s.page}>
    <header className={s.header}><Link href="/" className={s.brand}>AICTE Approval & Compliance</Link><Link href="/">Home</Link></header>
    <main className={s.loginCard} id="main-content">
      <p className={s.kicker}>LIVE WORKSPACE</p>
      <h1>Sign in</h1>
      <p>Use an authorised Supabase account linked to your application role and scope.</p>
      {!configured && <p role="alert" className={s.alert}>Live sign-in is waiting for the Supabase project URL and publishable key in the frontend environment.</p>}
      {error && <p role="alert" className={s.alert}>{error}</p>}
      {identity && <p><Link href="/portal">Continue as {identity.user.display_name}</Link></p>}
      <form onSubmit={submit} className={s.form}>
        <label>Email<input type="email" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)} disabled={!configured || busy} /></label>
        <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} disabled={!configured || busy} /></label>
        <button type="submit" disabled={!configured || loading || busy}>{busy ? "Checking access…" : "Sign in"}</button>
      </form>
      <p className={s.note}>Account access requires an active application user and approved scoped assignment. Sign-in alone does not grant access to records.</p>
    </main>
  </div>;
}
