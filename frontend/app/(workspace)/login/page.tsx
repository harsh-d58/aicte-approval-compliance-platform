"use client";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Icon, { type IconName } from "@/app/components/Icon";
import { roleNames, safeReturnTo } from "@/lib/portal/view-models";
import type { Role } from "@/lib/portal/types";
import { useDemo } from "@/app/portal-ui/DemoProvider";
import { Arrow, Brand } from "@/app/portal-ui/ui";
import s from "@/app/portal-ui/portal.module.css";

const icons: Record<Role, IconName> = { INSTITUTION: "institution", SCRUTINY: "search", REGIONAL: "map", EVC_COORDINATOR: "calendar", EVC_EXPERT: "user", COMPLIANCE: "shield", CENTRAL: "monitor", POLICY: "settings", AUDITOR: "document", SYSTEM: "settings" };
export default function LoginPage() {
  const { allData, loading, error, signIn, reload, user } = useDemo();
  const [selected, setSelected] = useState("user-institution");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();
  const personas = allData?.users.filter((u, index, users) => users.findIndex(other => other.assignments[0].role === u.assignments[0].role) === index) ?? [];
  const selectedUser = allData?.users.find(u => u.id === selected);
  function enter() {
    if (!selectedUser || submitting) return;
    setSubmitting(true); signIn(selectedUser.id);
    const destination = safeReturnTo(new URLSearchParams(window.location.search).get("returnTo"));
    router.push(selectedUser.assignments.length > 1 ? `/portal/access?returnTo=${encodeURIComponent(destination)}` : destination);
  }
  return <div className={s.authPage}><header className={s.authHeader}><Brand /><Link href="/" className={s.backLink}><Arrow back />Back to home</Link></header>
    <main id="main-content" className={s.authMain}><section className={s.authIntro}><span className={s.eyebrow}>ONE PLATFORM. EVERY STAGE.</span><h1>A clearer path.<br /><span>A connected workspace.</span></h1><p>From your first submission to the final decision, bring every application, document and next step into focus.</p><Image src="/footprint.png" alt="Connected digital services on desktop, tablet and mobile" width={560} height={400} className={s.authIllustration} unoptimized /><span className={s.authFeature}><Icon name="shield" size={14} />Scoped access</span><span className={s.authFeature}><Icon name="check" size={14} />Traceable decisions</span></section>
    <section className={s.authCard} aria-labelledby="signin-title"><span className={s.eyebrow}>WELCOME TO YOUR PORTAL</span><h2 id="signin-title">Let’s get you started.</h2><p>Choose a demonstration role to explore your workspace.</p><div className={s.authDemoLabel}><span>EXPLORE AS</span><span className={s.demoChip}>Demo access</span></div>
      {loading ? <p role="status">Loading demonstration profiles…</p> : error ? <div role="alert"><p>{error}</p><button onClick={reload} className={s.secondaryButton}>Try again</button></div> : <><div className={s.roleGrid} role="group" aria-label="Demonstration roles">{personas.map(person => { const role = person.assignments[0].role; return <button type="button" key={person.id} className={s.roleButton} aria-pressed={selected === person.id} onClick={() => setSelected(person.id)}><Icon name={icons[role]} size={17} /><span>{roleNames[role]}</span></button>; })}</div>
      {selectedUser && <div className={s.selectedUser}><span className={s.avatar}>{selectedUser.displayName.split(" ").map(n => n[0]).join("")}</span><span><strong>{selectedUser.displayName}</strong><small>Fictional profile · no password needed</small></span></div>}
      <button type="button" className={s.primaryButton} disabled={!selectedUser || submitting} onClick={enter}>{submitting ? "Opening your workspace…" : "Enter demonstration portal"}<Arrow /></button>
      {user && <Link className={s.textLink} href="/portal">Continue as {user.displayName}<Arrow /></Link>}</>}
      <p className={s.authDisclaimer}>This is a prototype using fictional records.<br />No real credentials or institutional information are required.</p><div className={s.authDivider} /><div className={s.ssoNote}><Icon name="shield" size={17} /><span>Production sign-in will use an approved identity provider. Demonstration access does not grant access to real AICTE records.</span></div>
    </section></main><footer className={s.authFooter}><span>AICTE Approval & Compliance Platform</span><span>Prototype · Not an official AICTE portal</span></footer>
  </div>;
}
