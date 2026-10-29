"use client";
import { useState } from "react";
import { useLive } from "./LiveProvider";
import { useWorkspace, Page, Panel, Links, Table, Search, Meta, s, formatDateTime } from "./domain-ui";
import { csv } from "@/lib/portal/exports";
import { download } from "@/lib/portal/files";

interface VerificationResult {
    valid: boolean;
    simulation: boolean;
    simulated_event_id: string | null;
    total_events: number;
    genesis_hash: string | null;
    head_hash: string | null;
    verified_at: string;
    errors: Array<{ id: string; code: string }>;
    immutable_triggers_active: boolean;
    active_triggers: string[];
    recent_blocks: Array<{ id: string; action: string; previous_hash: string | null; event_hash: string | null; valid: boolean }>;
}

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
    return <Page title={mode === "verify" ? "Cryptographic Audit Ledger Verification" : "Audit Explorer"} description="Persisted audit records and server verification results.">
        <Links items={[["Audit explorer", "/portal/audit"], ["Cryptographic verification", "/portal/audit/verify"]]} />
        {mode === "list" ? <>
            <Panel title="Audit filter"><Search value={query} onChange={setQuery} label="Search actor, action, reason, date or correlation" />
                <button className={s.button} onClick={() => download(csv(events.map(e => ({ Actor: e.actorId, Action: e.action, Entity: e.entityId, At: e.at, Reason: e.reason, Correlation: e.correlationId, Hash: e.eventHash }))), "audit-events.csv")}>Export visible events ↓</button>
            </Panel>
            <Table columns={["Actor / time (IST)", "Action / entity", "Reason", "Digest"]} rows={events.map(e => [`${data.users.find(u => u.id === e.actorId)?.displayName ?? e.actorId} · ${formatDateTime(e.at)}`, `${e.action} · ${e.entityType} · ${e.entityId}`, e.reason, e.eventHash || "No digest recorded"])} />
        </> : <>
            <Panel title="SHA-256 chain verifier"><p>The server recomputes stored event hashes and checks predecessor links. Historical gaps are reported as failures.</p>
                <div className={s.actions}><button className={s.button} disabled={working} onClick={() => void verify()}>{working ? "Verifying…" : "Run Cryptographic Chain Verification"}</button>
                    <button className={s.button} disabled={working} onClick={() => void verify(true)}>Simulate Tamper Detection</button></div>
                <p className={s.note}>Simulation alters a copy in server memory and runs the verifier. Saved audit records remain intact.</p>
                {error && <p role="alert" className={s.error}>{error}</p>}
            </Panel>
            {result && <>
                <Panel title={result.simulation ? "Tamper simulation result" : "Ledger verification result"}>
                    <p role="status">{result.valid ? "Verification passed" : "Verification found integrity errors"} · {result.total_events} events · {result.errors.length} errors</p>
                    <Meta items={[["Verified at", formatDateTime(result.verified_at)], ["Genesis hash", result.genesis_hash ?? "Empty ledger"], ["Head hash", result.head_hash ?? "Empty ledger"], ["Immutability check", result.immutable_triggers_active ? "Protection trigger detected" : "Protection trigger not confirmed"], ["Enabled triggers", result.active_triggers.join(", ") || "None"], ["Simulated event", result.simulated_event_id ?? "Not applicable"]]} />
                </Panel>
                <Table columns={["Event", "Finding"]} rows={result.errors.map(e => [e.id, e.code])} />
                <Table columns={["Event", "Action", "Previous hash", "Event hash", "Result"]} rows={result.recent_blocks.map(b => [b.id, b.action, b.previous_hash ?? "Genesis", b.event_hash ?? "Missing", b.valid ? "Valid" : "Invalid"])} />
            </>}
        </>}
    </Page>;
}
