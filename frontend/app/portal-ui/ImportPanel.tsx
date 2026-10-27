"use client";
import { useState } from "react";
import { Panel, Field, ActionForm, Table, s } from "./domain-ui";
import { useDemo } from "./DemoProvider";
const fields = ["code", "name", "regionId", "type", "campusName", "city"] as const;
export function parseCsv(text: string) { const rows: string[][] = []; let row: string[] = [], cell = "", quoted = false; for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
        if (quoted && text[i + 1] === '"') {
            cell += '"';
            i++;
        }
        else
            quoted = !quoted;
    }
    else if (c === "," && !quoted) {
        row.push(cell);
        cell = "";
    }
    else if ((c === "\n" || c === "\r") && !quoted) {
        if (c === "\r" && text[i + 1] === "\n")
            i++;
        row.push(cell);
        if (row.some(v => v.trim()))
            rows.push(row);
        row = [];
        cell = "";
    }
    else
        cell += c;
} if (quoted)
    throw new Error("CSV contains an unclosed quoted field."); row.push(cell); if (row.some(v => v.trim()))
    rows.push(row); return rows; }
export default function ImportPanel() { const { data } = useDemo(); const [rows, setRows] = useState<string[][]>([]); const [mapping, setMapping] = useState<Record<string, string>>({}); const [error, setError] = useState(""); const header = rows[0] ?? []; const mapped = rows.slice(1).map(row => Object.fromEntries(fields.map(key => [key, row[Number(mapping[key])] ?? ""]))); const duplicates = mapped.filter((row, i) => !row.code || mapped.findIndex(r => r.code.toLowerCase() === row.code.toLowerCase()) !== i || data?.institutions.some(inst => inst.code.toLowerCase() === row.code.toLowerCase())); const complete = fields.every(key => mapping[key] !== undefined && mapping[key] !== ""); return <Panel title="Local institution import preview"><p>Upload a fictional CSV, map its columns, inspect duplicates and confirm before committing. Maximum 200 rows; code, name, regionId, type, campusName and city are required.</p><label className={s.field}>CSV file<input type="file" accept=".csv,text/csv" onChange={async (e) => { setError(""); try {
    const f = e.target.files?.[0];
    if (!f)
        return;
    if (f.size > 1024 * 1024)
        throw new Error("CSV must be under 1 MB.");
    const parsed = parseCsv(await f.text());
    if (parsed.length < 2 || parsed.length > 201)
        throw new Error("Choose a header plus 1–200 records.");
    setRows(parsed);
    setMapping(Object.fromEntries(fields.map(key => [key, parsed[0].includes(key) ? String(parsed[0].indexOf(key)) : ""])));
}
catch (err) {
    setError(err instanceof Error ? err.message : "Could not parse CSV");
} }}/></label>{error && <p className={s.error} role="alert">{error}</p>}{header.length > 0 && <><div className={s.fields}>{fields.map(key => <label key={key} className={s.field}>{key}<select value={mapping[key] ?? ""} onChange={e => setMapping(v => ({ ...v, [key]: e.target.value }))}><option value="">Map a source column…</option>{header.map((c, i) => <option key={i} value={i}>{c}</option>)}</select></label>)}</div><Table columns={[...fields]} rows={mapped.map(row => fields.map(key => row[key]))}/>{duplicates.length > 0 && <p className={s.error}>{duplicates.length} duplicate or empty codes; resolve the CSV before import.</p>}{complete && !duplicates.length && <ActionForm kind="institution.import" submit="Import previewed fictional records" build={() => ({ rows: mapped })}><Field name="reason" label="Import reason / source note"/><label className={s.check}><input type="checkbox" required/>I reviewed the mapped fields and confirm these are fictional demonstration records.</label></ActionForm>}</>}</Panel>; }
