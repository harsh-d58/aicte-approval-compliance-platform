"use client";
import { useState } from "react";
import { useWorkspace, Page, Panel, Links, Table, Search, Meta, s, formatDateTime } from "./domain-ui";
import { csv } from "@/lib/portal/exports";
import { download } from "@/lib/portal/files";
export default function AuditPages({ mode }: {
    mode: "list" | "verify";
}) { const { data, user, assignmentIndex } = useWorkspace(); const [query, setQuery] = useState(""); const [baseline, setBaseline] = useState(""); const [result, setResult] = useState(""); const [error, setError] = useState(""); if (!data || !user)
    return null; const events = data.auditEvents.filter(e => `${e.actorId} ${data.users.find(u => u.id === e.actorId)?.displayName} ${e.action} ${e.entityId} ${e.reason} ${e.at} ${e.correlationId}`.toLowerCase().includes(query.toLowerCase())); const key = `aicte.fingerprint.${user.id}.${assignmentIndex}`; const fingerprint = async () => { const bytes = new TextEncoder().encode(JSON.stringify({ applications: data.applications, documents: data.documents, meetingRecords: data.meetingRecords, conditions: data.conditions, auditEvents: data.auditEvents })); return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))).map(b => b.toString(16).padStart(2, "0")).join(""); }; return <Page title={mode === "verify" ? "Local integrity check" : "Audit explorer"} description="Traceable demonstration actions. Illustrative event hash strings are not cryptographic ledger proofs."><Links items={[["Audit explorer", "/portal/audit"], ["Integrity check", "/portal/audit/verify"]]}/>{mode === "list" ? <><Panel><Search value={query} onChange={setQuery} label="Search actor, action, reason, date or correlation"/><button className={s.button} onClick={() => download(csv(events.map(e => ({ Actor: data.users.find(u => u.id === e.actorId)?.displayName ?? e.actorId, Action: e.action, Entity: e.entityId, At: e.at, Reason: e.reason, Version: e.version, Correlation: e.correlationId, Anchor: e.anchor }))), "demo-audit.csv")}>Export visible events ↓</button></Panel><Table columns={["Actor / time (IST)", "Action / entity", "Reason", "Version / correlation", "Anchor"]} rows={events.map(e => [`${data.users.find(u => u.id === e.actorId)?.displayName ?? e.actorId} · ${formatDateTime(e.at)}`, `${e.action} · ${e.entityType} · ${e.entityId}`, e.reason, `${e.version} · ${e.correlationId}`, e.anchor])}/></> : <Panel title="Capture & compare a local SHA-256 fingerprint"><p>This hashes your currently scoped demo records in the browser. Capture a baseline, make a change, then compare. A mismatch means local content changed; a match does not establish issuer authenticity or prove that a server audit chain is valid.</p><div className={s.actions}><button className={s.button} onClick={async () => { try {
    const hash = await fingerprint();
    sessionStorage.setItem(key, hash);
    setBaseline(hash);
    setResult("Baseline captured for this identity and scope.");
}
catch (e) {
    setError(e instanceof Error ? e.message : "Fingerprint unavailable");
} }}>Capture baseline</button><button className={s.button} onClick={async () => { try {
    const previous = baseline || sessionStorage.getItem(key);
    if (!previous)
        throw new Error("Capture a baseline first.");
    const current = await fingerprint();
    setBaseline(previous);
    setResult(current === previous ? "MATCH — scoped records match the locally captured baseline." : "MISMATCH — scoped records changed since the locally captured baseline.");
}
catch (e) {
    setError(e instanceof Error ? e.message : "Comparison failed");
} }}>Compare current records</button></div>{result && <p role="status" className={s.success}>{result}</p>}{error && <p role="alert" className={s.error}>{error}</p>}{baseline && <pre className={s.source}>{baseline}</pre>}<Meta items={[["Algorithm", "Web Crypto SHA-256"], ["Source", "Current scoped browser records"], ["Authority / anchor", "Local only · authoritative service disconnected"]]}/></Panel>}</Page>; }
