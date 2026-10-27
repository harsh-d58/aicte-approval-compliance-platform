/** Small dependency-free writers for actual CSV, OOXML workbooks and paginated PDF reports. */
export type ReportRow = Record<string, string | number>;
const enc = new TextEncoder();
const xml = (v: unknown) => String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const safe = (v: unknown) => /^[=+@\-\t\r]/.test(String(v)) ? `'${v}` : String(v);
export function csv(rows: ReportRow[], columns = Object.keys(rows[0] ?? {}), metadata: string[] = []) { return new Blob(["\uFEFF", [...metadata.map(m => [m]), columns, ...rows.map(r => columns.map(c => r[c] ?? ""))].map(row => row.map(v => `"${safe(v).replaceAll('"', '""')}"`).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" }); }
function zip(files: Record<string, string>) { const chunks: Uint8Array[] = []; const central: Uint8Array[] = []; let offset = 0; const u16 = (v: DataView, i: number, n: number) => v.setUint16(i, n, true); const u32 = (v: DataView, i: number, n: number) => v.setUint32(i, n, true); for (const [path, text] of Object.entries(files)) {
    const name = enc.encode(path), body = enc.encode(text);
    let crc = 0xffffffff;
    for (const b of body) {
        crc ^= b;
        for (let i = 0; i < 8; i++)
            crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    crc = (crc ^ 0xffffffff) >>> 0;
    const head = new Uint8Array(30 + name.length);
    const h = new DataView(head.buffer);
    u32(h, 0, 0x04034b50);
    u16(h, 4, 20);
    u32(h, 14, crc);
    u32(h, 18, body.length);
    u32(h, 22, body.length);
    u16(h, 26, name.length);
    head.set(name, 30);
    chunks.push(head, body);
    const dir = new Uint8Array(46 + name.length);
    const d = new DataView(dir.buffer);
    u32(d, 0, 0x02014b50);
    u16(d, 4, 20);
    u16(d, 6, 20);
    u32(d, 16, crc);
    u32(d, 20, body.length);
    u32(d, 24, body.length);
    u16(d, 28, name.length);
    u32(d, 42, offset);
    dir.set(name, 46);
    central.push(dir);
    offset += head.length + body.length;
} const size = central.reduce((n, b) => n + b.length, 0); const end = new Uint8Array(22); const e = new DataView(end.buffer); u32(e, 0, 0x06054b50); u16(e, 8, central.length); u16(e, 10, central.length); u32(e, 12, size); u32(e, 16, offset); return [...chunks, ...central, end]; }
export function xlsx(rows: ReportRow[], columns = Object.keys(rows[0] ?? {}), metadata: string[] = []) { const all = [...metadata.map(m => [m]), columns, ...rows.map(r => columns.map(c => r[c] ?? ""))]; const col = (i: number): string => i < 26 ? String.fromCharCode(65 + i) : col(Math.floor(i / 26) - 1) + col(i % 26); const sheet = `<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${all.map((row, i) => `<row r="${i + 1}">${row.map((v, j) => `<c r="${col(j)}${i + 1}" ${typeof v === "number" ? 't="n"' : 't="inlineStr"'}>${typeof v === "number" ? `<v>${v}</v>` : `<is><t xml:space="preserve">${xml(v)}</t></is>`}</c>`).join("")}</row>`).join("")}</sheetData></worksheet>`; const files = { "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>', "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>', "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>', "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>', "xl/worksheets/sheet1.xml": sheet }; return new Blob(zip(files) as BlobPart[], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }); }
export function pdf(rows: ReportRow[], columns = Object.keys(rows[0] ?? {}), metadata: string[] = []) { const ascii = (v: string) => v.normalize("NFKD").replace(/[^\x20-\x7e]/g, "?"); const lines = ["AICTE FRONTEND DEMONSTRATION REPORT", ...metadata, `${rows.length} records`, ...rows.flatMap((r, i) => ["", `Record ${i + 1}`, ...columns.flatMap(c => { const text = ascii(`${c}: ${r[c] ?? ""}`); return text.match(/.{1,100}/g) ?? [""]; })])].map(ascii); const pages: Array<string[]> = []; for (let i = 0; i < lines.length; i += 48)
    pages.push(lines.slice(i, i + 48)); const objects: string[] = []; const add = (s: string) => { objects.push(s); return objects.length; }; add("<< /Type /Catalog /Pages 2 0 R >>"); add(""); const font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"); const ids: number[] = []; for (const [index, page] of pages.entries()) {
    const content = `BT /F1 9 Tf 14 TL 40 800 Td ${[...page, `Page ${index + 1} of ${pages.length}`].map((line, i) => `${i ? "T* " : ""}(${line.replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)")}) Tj`).join("\n")} ET`;
    const stream = add(`<< /Length ${enc.encode(content).length} >>\nstream\n${content}\nendstream`);
    ids.push(add(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${font} 0 R >> >> /Contents ${stream} 0 R >>`));
} objects[1] = `<< /Type /Pages /Count ${ids.length} /Kids [${ids.map(i => `${i} 0 R`).join(" ")}] >>`; let output = "%PDF-1.4\n"; const offsets = [0]; objects.forEach((o, i) => { offsets.push(enc.encode(output).length); output += `${i + 1} 0 obj\n${o}\nendobj\n`; }); const start = enc.encode(output).length; output += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.slice(1).map(o => `${String(o).padStart(10, "0")} 00000 n \n`).join("")}trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${start}\n%%EOF`; return new Blob([output], { type: "application/pdf" }); }
