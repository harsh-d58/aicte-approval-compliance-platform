import { formatDateTime } from "@/lib/portal/view-models";
import styles from "./AuditVerification.module.css";

export interface VerificationResult {
    local_demo?: boolean;
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
    recent_blocks: Array<{ id: string; action: string; actor_id?: string | null; entity_type?: string; entity_id?: string; event_at?: string; previous_hash: string | null; event_hash: string | null; valid: boolean }>;
}

const explanations: Record<string, string> = {
    HASH_INVALID: "Stored content no longer matches its SHA-256 digest.",
    PREDECESSOR_INVALID: "The previous-hash link does not match the preceding event.",
    LEGACY_UNCHAINED: "This historical event has no recorded digest.",
    ORDER_INVALID: "Events are not in the required chronological order.",
};
const displayAction = (action: string) => action.toLowerCase().replaceAll("_", " ").replace(/^./, c => c.toUpperCase());

export function verificationHeadline(result: VerificationResult): string {
    if (result.simulation) return result.valid ? "Simulation completed: no integrity error detected" : "Tamper detected in the simulated copy";
    return result.valid && result.errors.length === 0
        ? "SUCCESS: Cryptographic hash chain intact and mathematically valid"
        : "Verification failed: audit integrity errors detected";
}

function Digest({label, value, empty = "Empty ledger"}: {label: string; value: string | null; empty?: string}) {
    return <div><dt>{label}</dt><dd><code>{value ?? empty}</code></dd></div>;
}

export default function AuditVerification({result, actorNames}: {result: VerificationResult; actorNames: Record<string, string>}) {
    const passed = result.valid && result.errors.length === 0;
    const heading = verificationHeadline(result);
    return <div className={styles.results}>
        <section className={styles.panel} aria-labelledby="verification-result-title">
            <h2 id="verification-result-title">{result.simulation ? "Tamper simulation result" : "Ledger verification result"}</h2>
            {result.local_demo && <p>Browser-local demo ledger. Hashes demonstrate integrity checks; they are not an independently protected database audit trail. Database triggers and external anchoring are unavailable.</p>}
            <p role="status" className={result.simulation ? styles.simulation : passed ? styles.success : styles.failure}>{heading}</p>
            {result.simulation && <p>The stored ledger was not changed. This result belongs to an in-memory tamper test; run Verify cryptographic chain to check the saved ledger.</p>}
            <div className={styles.summary}>
                <div><span>Events checked</span><strong>{result.total_events.toLocaleString("en-IN")}</strong></div>
                <div><span>Integrity findings</span><strong>{result.errors.length}</strong></div>
                <div><span>Verified at (IST)</span><strong className={styles.timestamp}>{formatDateTime(result.verified_at)}</strong></div>
            </div>
            <p className={styles.protection}><strong>Database protection:</strong> {result.immutable_triggers_active ? "Immutability trigger detected" : "Immutability trigger not confirmed"}. This check is reported separately from hash-chain validity.</p>
            <details className={styles.details}><summary>Inspect chain fingerprints and protection details</summary>
                <dl className={styles.digests}><Digest label="Genesis SHA-256" value={result.genesis_hash}/><Digest label="Head SHA-256" value={result.head_hash}/>
                    <div><dt>Enabled triggers</dt><dd>{result.active_triggers.join(", ") || "None reported"}</dd></div>
                    {result.simulated_event_id && <div><dt>Simulated event</dt><dd><code>{result.simulated_event_id}</code></dd></div>}
                </dl>
            </details>
        </section>
        <section className={styles.panel}>
            <h2>Integrity findings</h2>
            {!result.errors.length ? <p>No integrity errors were reported in the checked ledger.</p> : <div className={styles.tableWrap}><table className={styles.table}>
                <thead><tr><th>Event</th><th>Check</th><th>Finding</th></tr></thead>
                <tbody>{result.errors.map((error, index)=><tr key={`${error.id}-${error.code}-${index}`}><td><code>{error.id}</code></td><td>{displayAction(error.code)}</td><td>{explanations[error.code] ?? "The server reported this integrity finding."}</td></tr>)}</tbody>
            </table></div>}
        </section>
        <section className={styles.panel}>
            <h2>Recent verified events</h2>
            <p className={styles.caption}>Showing the latest {result.recent_blocks.length} of {result.total_events.toLocaleString("en-IN")} checked events, oldest to newest. The verification covers the full ledger.</p>
            {!result.recent_blocks.length ? <p>The ledger contains no recent events to display.</p> : <div className={styles.tableWrap}><table className={styles.table}>
                <thead><tr><th>Time / actor (IST)</th><th>Action / record</th><th>Integrity</th><th>Hash evidence</th></tr></thead>
                <tbody>{result.recent_blocks.map(block=><tr key={block.id}>
                    <td>{block.event_at ? formatDateTime(block.event_at) : "Time not reported"}<small>{block.actor_id ? actorNames[block.actor_id] ?? block.actor_id : "System / actor not recorded"}</small></td>
                    <td><strong>{displayAction(block.action)}</strong><small>{block.entity_type ? displayAction(block.entity_type) : "Audit event"}</small><code>{block.entity_id ?? block.id}</code></td>
                    <td><span className={block.valid ? styles.validBadge : styles.invalidBadge}>{block.valid ? "Verified" : "Failed"}</span></td>
                    <td><details><summary>Inspect hashes</summary><dl className={styles.digests}><Digest label="Event SHA-256" value={block.event_hash} empty="Missing digest"/><Digest label="Previous SHA-256" value={block.previous_hash} empty="Genesis / no predecessor"/><div><dt>Audit event ID</dt><dd><code>{block.id}</code></dd></div></dl></details></td>
                </tr>)}</tbody>
            </table></div>}
        </section>
    </div>;
}
