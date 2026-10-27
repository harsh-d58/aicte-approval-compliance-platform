"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useWorkspace, Page, Panel, Links, Table, Unavailable, Meta, Link, Badge, s, formatDateTime } from "./domain-ui";
import { getReportRows } from "@/lib/portal/report-rows";
import { csv, xlsx, pdf, type ReportRow } from "@/lib/portal/exports";
import { download } from "@/lib/portal/files";
import { demoNow, scopeName } from "@/lib/portal/view-models";
import type { PortalCollections } from "@/lib/portal/types";
export function reportData(data: PortalCollections, filters: Record<string, string>) { const apps = data.applications.filter(a => (!filters.regionId || data.institutions.find(i => i.id === a.institutionId)?.regionId === filters.regionId) && (!filters.status || a.status === filters.status) && (!a.submittedAt || (!filters.dateFrom || a.submittedAt.slice(0, 10) >= filters.dateFrom) && (!filters.dateTo || a.submittedAt.slice(0, 10) <= filters.dateTo))); const appIds = new Set(apps.map(a => a.id)); const visits = data.visits.filter(v => appIds.has(v.applicationId)); const conditions = data.conditions.filter(c => appIds.has(c.applicationId)); const selected = { ...data, applications: apps, institutions: data.institutions.filter(i => !filters.regionId || i.regionId === filters.regionId), regions: data.regions.filter(r => !filters.regionId || r.id === filters.regionId), visits, slots: data.slots.filter(s => visits.some(v => v.id === s.visitId)), conditions, documents: data.documents.filter(d => (!d.applicationId || appIds.has(d.applicationId)) && (!filters.regionId || data.institutions.find(i => i.id === d.institutionId)?.regionId === filters.regionId)), tasks: data.tasks.filter(t => !t.applicationId || appIds.has(t.applicationId)), notifications: data.notifications.filter(n => (!filters.dateFrom || n.createdAt.slice(0, 10) >= filters.dateFrom) && (!filters.dateTo || n.createdAt.slice(0, 10) <= filters.dateTo)) }; return selected; }
export default function ReportPages({ mode }: {
    mode: "list" | "detail" | "run";
}) {
    const { data, allData, params, user, assignmentIndex, router, execute } = useWorkspace();
    const search = useSearchParams();
    const [columnFilters, setColumns] = useState<Record<string, string>>({});
    const [query, setQuery] = useState(search.get("query") ?? "");
    const [regionId, setRegion] = useState(search.get("regionId") ?? "");
    const [status, setStatus] = useState(search.get("status") ?? "");
    const [from, setFrom] = useState("2026-01-01");
    const [to, setTo] = useState("2026-12-31");
    const [error, setError] = useState("");
    const [working, setWorking] = useState(false);
    if (!data || !user)
        return null;
    const scopedData = allData && ["CENTRAL", "SYSTEM", "AUDITOR"].includes(user.assignments[assignmentIndex].role) && user.assignments[assignmentIndex].scope.type === "GLOBAL" ? { ...data, notifications: allData.notifications } : data;
    const scope = scopeName(data, user, assignmentIndex);
    const definition = data.reportDefinitions.find(r => r.id === params.reportCode);
    const run = data.reportRuns.find(r => r.id === params.runId);
    const filter = { query, regionId, status, dateFrom: from, dateTo: to };
    const baseRows = definition ? getReportRows(definition.id, reportData(scopedData, filter)) : [];
    const rows = baseRows.filter(r => Object.values(r).join(" ").toLowerCase().includes(query.toLowerCase()) && Object.entries(columnFilters).every(([key, value]) => !value || String(r[key] ?? "") === value));
    const columns = definition?.columns ?? [];
    const exportsFor = (values: ReportRow[], cols: string[], name: string, metadata: string[]) => [<button key="csv" className={s.button} onClick={() => download(csv(values, cols, metadata), `${name}.csv`)}>CSV ↓</button>, <button key="xlsx" className={s.button} onClick={() => download(xlsx(values, cols, metadata), `${name}.xlsx`)}>Excel ↓</button>, <button key="pdf" className={s.button} onClick={() => download(pdf(values, cols, metadata), `${name}.pdf`)}>PDF ↓</button>];
    if (mode === "list")
        return <Page title="Reports" description="Eight defined report outputs, filtered from the same scoped records as the workspaces."><div className={s.grid}>{data.reportDefinitions.map(d => <Panel key={d.id} title={d.name}><p>{d.columns.join(" · ")}</p><Link className={s.link} href={`/portal/reports/${d.id}`}>Open report →</Link></Panel>)}</div><Panel title="Export runs"><Table columns={["Report", "Status", "Rows", "Snapshot"]} rows={data.reportRuns.map(r => [<Link key={r.id} href={`/portal/report-runs/${r.id}`}>{r.reportCode}</Link>, r.status, r.rowCount, formatDateTime(r.snapshotAt)])}/></Panel></Page>;
    if (mode === "run") {
        if (!run)
            return <Unavailable name="Report run"/>;
        const d = data.reportDefinitions.find(d => d.id === run.reportCode);
        const frozen = run.snapshotRows;
        return <Page title="Export run" description={run.id}><Links items={[["Report catalogue", "/portal/reports"], ["Report viewer", `/portal/reports/${run.reportCode}`]]}/><Panel><Meta items={[["Status", <Badge key="s" status={run.status}/>], ["Period", `${run.period.from} – ${run.period.to}`], ["Snapshot", formatDateTime(run.snapshotAt)], ["Requested by", data.users.find(u => u.id === run.requestedBy)?.displayName], ["Rows", run.rowCount], ["Filters", JSON.stringify(run.filters)]]}/>{run.failureReason && <p className={s.error}>{run.failureReason}</p>}{run.status === "COMPLETED" && frozen ? <div className={s.actions}>{exportsFor(frozen, d?.columns ?? Object.keys(frozen[0] ?? {}), run.id, [`Scope: ${scope}`, `Period: ${run.period.from} – ${run.period.to}`, `Snapshot: ${run.snapshotAt}`, `Filters: ${JSON.stringify(run.filters)}`])}</div> : run.status === "COMPLETED" ? <p className={s.note}>This seeded run has metadata only. Generate a new export from the viewer to capture and download a real snapshot.</p> : run.status === "EXPIRED" ? <p>Download expired. Generate a fresh export from the viewer.</p> : <button className={s.button} onClick={() => router.push(`/portal/reports/${run.reportCode}`)}>Retry with current scoped data</button>}</Panel></Page>;
    }
    if (!definition)
        return <Unavailable name="Report"/>;
    return <Page title={definition.name} description={`${scope} · snapshot ${formatDateTime(demoNow)} · period filters use submission dates for case reports and event dates for delivery reports.`}><Links items={[["Report catalogue", "/portal/reports"]]}/><Panel title="Report filters"><div className={s.fields}><label className={s.field}>Search report rows<input type="search" value={query} onChange={e => setQuery(e.target.value)}/></label><label className={s.field}>Region<select value={regionId} onChange={e => setRegion(e.target.value)}><option value="">All authorised regions</option>{data.regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label><label className={s.field}>Application status<select value={status} onChange={e => setStatus(e.target.value)}><option value="">All statuses</option>{[...new Set(data.applications.map(a => a.status))].map(s => <option key={s}>{s}</option>)}</select></label><label className={s.field}>From<input type="date" value={from} max={to} onChange={e => setFrom(e.target.value)}/></label><label className={s.field}>Through<input type="date" value={to} min={from} onChange={e => setTo(e.target.value)}/></label></div><details className={s.item}><summary>Report-specific filters</summary><div className={s.fields}>{columns.map(column => <label className={s.field} key={column}>{column}<select value={columnFilters[column] ?? ""} onChange={e => setColumns(v => ({ ...v, [column]: e.target.value }))}><option value="">All values</option>{[...new Set(baseRows.map(r => String(r[column] ?? "")))].filter(Boolean).map(value => <option key={value}>{value}</option>)}</select></label>)}</div></details><div className={s.actions}><button className={s.button} onClick={() => { setQuery(""); setColumns({}); setRegion(""); setStatus(""); setFrom("2026-01-01"); setTo("2026-12-31"); }}>Clear filters</button><button className={s.button} disabled={working || !from || !to || from > to} onClick={async () => { setWorking(true); setError(""); let id = ""; try {
        const result = execute({ kind: "report.create", values: { reportCode: definition.id, ...filter, columnFilters: JSON.stringify(columnFilters) } });
        id = result.id;
        await new Promise(resolve => setTimeout(resolve, 250));
        execute({ kind: "report.complete", id, values: { rowCount: rows.length, rows } });
        router.push(`/portal/report-runs/${id}`);
    }
    catch (e) {
        const message = e instanceof Error ? e.message : "Export failed";
        setError(message);
        if (id)
            try { execute({ kind: "report.complete", id, values: { rowCount: 0, failure: message } }); } catch { /* A changed session cannot finish work in the previous scope. */ }
    }
    finally {
        setWorking(false);
    } }}>{working ? "Generating snapshot…" : "Generate export snapshot"}</button></div>{error && <p role="alert" className={s.error}>{error}</p>}</Panel><Table columns={columns} caption={`${rows.length} scoped records · fixed demonstration clock`} rows={rows.map(r => columns.map(c => String(r[c] ?? "—")))}/><Panel title="Case drill-through"><p>Open source records to inspect the values used above.</p><Links items={definition.id === "notification-delivery" ? scopedData.notifications.filter(n => rows.some(r => r.Event === n.event && r.Channel === n.channel && r["Delivery status"] === n.status)).map(n => [n.event, `/portal/notifications/${n.id}`]) : definition.id === "undertaking-compliance" ? scopedData.conditions.filter(c => rows.some(r => r.Condition === c.code)).map(c => [c.code, `/portal/compliance/${c.id}`]) : definition.id === "document-validity" ? scopedData.documents.filter(doc => rows.some(r => r["Document type"] === doc.type && r.Institution === scopedData.institutions.find(i => i.id === doc.institutionId)?.name)).map(doc => [doc.reference, `/portal/documents/${doc.id}`]) : reportData(scopedData, filter).applications.filter(a => rows.some(r => r.Application === a.number || r.Case === a.id || r.Region === scopedData.regions.find(region => region.id === scopedData.institutions.find(i => i.id === a.institutionId)?.regionId)?.name)).map(a => [a.number, `/portal/applications/${a.id}`])}/></Panel></Page>;
}
