"use client";
import { useState } from "react";
import { useLive } from "./LiveProvider";
import { useWorkspace, Page, Panel, Links, Table, Search, s, formatDateTime } from "./domain-ui";
import AuditVerification, { type VerificationResult } from "./AuditVerification";
import { csv } from "@/lib/portal/exports";
import { download } from "@/lib/portal/files";
import { isDemoMode } from "@/lib/portal/mode";

export default function AuditPages({ mode }: { mode: "list" | "verify" }) {
    const { data, user } = useWorkspace();
    const live = useLive();
    const [query, setQuery] = useState("");
    const [working, setWorking] = useState(false);
    const [result, setResult] = useState<VerificationResult | null>(null);
    const [error, setError] = useState("");
    if (!data || !user) return null;
    const events = data.auditEvents.filter(e => `${e.actorId} ${e.action} ${e.entityId} ${e.reason} ${e.at} ${e.correlationId}`.toLowerCase().includes(query.toLowerCase()));
    async function verify(simulate = false) {
        setWorking(true); setError(""); setResult(null);
        try {
            setResult(await live.get<VerificationResult>(`/audit/verify-chain?limit_recent=8&simulate=${simulate}`));
        } catch (cause) { setError(cause instanceof Error ? cause.message : "Audit verification failed."); }
        finally { setWorking(false); }
    }
    return <Page title={mode === "verify" ? "Cryptographic Audit Ledger Verification" : "Audit Explorer"} description={isDemoMode ? "Browser-local demonstration events and integrity verification." : "Persisted audit records and server verification results."}>
        <Links items={[["Audit explorer", "/portal/audit"], ["Cryptographic verification", "/portal/audit/verify"]]} />
        {mode === "list" ? <>
            <Panel title="Audit filter"><Search value={query} onChange={setQuery} label="Search actor, action, reason, date or correlation" />
                <button className={s.button} onClick={() => download(csv(events.map(e => ({ Actor: e.actorId, Action: e.action, Entity: e.entityId, At: e.at, Reason: e.reason, Correlation: e.correlationId, Hash: e.eventHash }))), "audit-events.csv")}>Export visible events ↓</button>
            </Panel>
            <Table columns={["Actor / time (IST)", "Action / entity", "Reason / correlation", "Digest"]} rows={events.map(e => [`${data.users.find(u => u.id === e.actorId)?.displayName ?? e.actorId} · ${formatDateTime(e.at)}`, `${e.action} · ${e.entityType} · ${e.entityId}`, <span key="reason">{e.reason}<small>Correlation: {e.correlationId || "Not recorded"}</small></span>, <code key="hash" style={{overflowWrap:"anywhere"}}>{e.eventHash || "No digest recorded"}</code>])} />
        </> : <>
            <Panel title="SHA-256 chain verifier"><p>{isDemoMode ? "This browser recomputes local event hashes and predecessor links. Verification does not claim database immutability." : "The server recomputes stored event hashes and checks predecessor links. Historical gaps are reported as failures."}</p>
                <div className={s.actions}><button className={s.button} disabled={working} onClick={() => void verify()}>{working ? "Verifying…" : "Verify cryptographic chain"}</button>
                    <button className={s.button} disabled={working} onClick={() => void verify(true)}>Simulate Tamper Detection</button></div>
                <p className={s.note}>Simulation alters a copy in server memory and runs the verifier. Saved audit records remain intact.</p>
                {error && <p role="alert" className={s.error}>{error}</p>}
            </Panel>
            {result && <AuditVerification result={result} actorNames={Object.fromEntries(data.users.map(user=>[user.id,user.displayName]))}/>}
        </>}
    </Page>;
}
