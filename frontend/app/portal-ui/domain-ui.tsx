"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useDemo } from "./DemoProvider";
import { Badge, Empty, PageHeading } from "./ui";
import { humanize, formatDateTime } from "@/lib/portal/view-models";
import type { Command, CommandKind, CommandResult } from "@/lib/portal/commands";
import s from "./domain.module.css";
export { s, Link, Badge, Empty, humanize, formatDateTime };
export function useWorkspace() { const context = useDemo(); const params = useParams<Record<string, string>>(); const router = useRouter(); const role = context.user?.assignments[context.assignmentIndex]?.role; return { ...context, params, router, role, allowed: (...roles: string[]) => !!role && roles.includes(role) }; }
export function Page({ title, description, children, actions }: {
    title: string;
    description: string;
    children: React.ReactNode;
    actions?: React.ReactNode;
}) { return <div className={s.page}><PageHeading eyebrow="APPROVAL & COMPLIANCE · DEMONSTRATION" title={title} description={description} action={actions}/>{children}</div>; }
export function Panel({ title, children }: {
    title?: string;
    children: React.ReactNode;
}) { return <section className={s.panel}>{title && <h2>{title}</h2>}{children}</section>; }
export function Links({ items }: {
    items: [
        string,
        string
    ][];
}) { return <nav className={s.chips} aria-label="Related workspaces">{items.map(([label, href]) => <Link key={href} href={href}>{label} →</Link>)}</nav>; }
export function Field({ name, label, type = "text", value, options, required = true, hint }: {
    name: string;
    label: string;
    type?: string;
    value?: string | number;
    options?: {
        id: string;
        name: string;
    }[];
    required?: boolean;
    hint?: string;
}) { return <label className={s.field}>{label}{options ? <select name={name} defaultValue={value ?? ""} required={required}><option value="">Choose…</option>{options.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select> : type === "textarea" ? <textarea name={name} defaultValue={value} required={required}/> : <input name={name} type={type} defaultValue={value} required={required} step={type === "number" ? "any" : undefined}/>}{hint && <small>{hint}</small>}</label>; }
export function Checks({ name, options, selected = [] }: {
    name: string;
    options: {
        id: string;
        name: string;
    }[];
    selected?: string[];
}) { return <div className={s.list}>{options.map(o => <label className={s.check} key={o.id}><input name={name} type="checkbox" value={o.id} defaultChecked={selected.includes(o.id)}/>{o.name}</label>)}</div>; }
export function ActionForm({ kind, id, version, title, children, build, after, defaults = {}, submit = "Save changes" }: {
    kind: CommandKind;
    id?: string;
    version?: number;
    title?: string;
    children?: React.ReactNode;
    build?: (fd: FormData) => Record<string, unknown> | Promise<Record<string, unknown>>;
    after?: (result: CommandResult) => void;
    defaults?: Record<string, unknown>;
    submit?: string;
}) {
    const { execute } = useDemo();
    const [error, setError] = useState("");
    const [done, setDone] = useState("");
    const [pending, setPending] = useState(false);
    const observedVersion = useRef(version);
    const dirty = useRef(false);
    const busy = useRef(false);
    useEffect(() => { const guard = (e: BeforeUnloadEvent) => { if (dirty.current) {
        e.preventDefault();
    } }; const navigation = (e: MouseEvent) => { const a = (e.target as Element)?.closest?.("a[href]"); if (a && dirty.current && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
        if (!window.confirm("Discard unsaved input before leaving this form?")) {
            e.preventDefault();
            e.stopImmediatePropagation();
        }
        else
            dirty.current = false;
    } }; window.addEventListener("beforeunload", guard); document.addEventListener("click", navigation, true); return () => { window.removeEventListener("beforeunload", guard); document.removeEventListener("click", navigation, true); }; }, []);
    return <form className={s.form} onChange={() => { dirty.current = true; setDone(""); }} onSubmit={async (e) => { e.preventDefault(); if (busy.current)
        return; busy.current = true; setPending(true); setError(""); setDone(""); try {
        const fd = new FormData(e.currentTarget);
        const values: Record<string, unknown> = { ...defaults };
        for (const key of new Set(fd.keys())) {
            const entries = fd.getAll(key);
            values[key] = key.endsWith("Ids") ? entries.map(String) : entries.length > 1 ? entries : entries[0];
        }
        const command: Command = { kind, id, expectedVersion: observedVersion.current, values: { ...values, ...(build ? await build(fd) : {}) } };
        const result = execute(command);
        dirty.current = false;
        const updated = result.data.applications.find(a => a.id === id) ?? result.data.visits.find(v => v.id === id);
        observedVersion.current = updated?.version ?? result.data.meetingRecords.find(r => r.id === id)?.currentVersion ?? observedVersion.current;
        setDone(result.message);
        after?.(result);
    }
    catch (err) {
        setError(err instanceof Error ? err.message : "Action failed. Your input has been retained.");
    }
    finally {
        busy.current = false;
        setPending(false);
    } }}>{title && <h3>{title}</h3>}{error && <p role="alert" tabIndex={-1} className={s.error}>{error}</p>}{done && <p role="status" className={s.success}>{done}</p>}{children}<div className={s.actions}><button className={s.button} type="submit" disabled={pending}>{pending ? "Saving…" : submit}</button><button className={s.button} type="button" onClick={e => { if (!dirty.current || window.confirm("Discard the unsaved input in this form?")) {
        e.currentTarget.form?.reset();
        dirty.current = false;
        observedVersion.current = version;
        setError("");
        setDone("");
    } }}>Reset form</button></div></form>;
}
export function ReasonAction({ kind, id, version, label, children, defaults, after }: {
    kind: CommandKind;
    id: string;
    version?: number;
    label: string;
    children?: React.ReactNode;
    defaults?: Record<string, unknown>;
    after?: (r: CommandResult) => void;
}) { return <ActionForm kind={kind} id={id} version={version} title={label} submit={label} defaults={defaults} after={after}>{children}<Field name="reason" label="Reason / review notes" type="textarea"/></ActionForm>; }
export function Table({ columns, rows, caption }: {
    columns: string[];
    rows: React.ReactNode[][];
    caption?: string;
}) { return rows.length ? <div className={s.tableWrap}><table className={s.table}>{caption && <caption>{caption}</caption>}<thead><tr>{columns.map(c => <th key={c} scope="col">{c}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody></table></div> : <Empty title="No matching records">Try different filters, or choose another authorised role and scope.</Empty>; }
export function Unavailable({ name = "Record" }: {
    name?: string;
}) { return <Page title={`${name} unavailable`} description="This record is outside the active scope or is unavailable."><Panel><Empty title="Choose an available record">This record does not exist in your active role and scope. <Link href="/portal/access">Review your scope</Link>.</Empty></Panel></Page>; }
export function Meta({ items }: {
    items: [
        string,
        React.ReactNode
    ][];
}) { return <dl className={s.meta}>{items.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value ?? "Not recorded"}</dd></div>)}</dl>; }
export function Search({ value, onChange, label = "Search records" }: {
    value: string;
    onChange: (v: string) => void;
    label?: string;
}) { return <label className={s.field}>{label}<input value={value} onChange={e => onChange(e.target.value)} type="search"/></label>; }
export function Versions({ name = "versionIds", institutionId }: {
    name?: string;
    institutionId?: string;
}) { const { data } = useDemo(); return <><p className={s.muted}>Select the exact evidence versions. Historical versions remain attached to earlier submissions.</p><Checks name={name} options={data?.documents.filter(d => !institutionId || d.institutionId === institutionId).flatMap(d => d.versions.map(v => ({ id: v.id, name: `${humanize(d.type)} · v${v.number} · ${v.fileName} · ${humanize(v.verification)}` }))) ?? []}/></>; }
export const valuesOf = (fd: FormData, key: string) => fd.getAll(key).map(String);
export const optionsOf = (values: string[]) => values.map(id => ({ id, name: humanize(id) }));
