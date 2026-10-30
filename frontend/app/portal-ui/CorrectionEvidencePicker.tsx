"use client";
import { useRef, useState } from "react";
import { compatibleEvidence } from "@/lib/live/deficiency-evidence";
import { putFile } from "@/lib/portal/files";
import { useWorkspace, humanize, s } from "./domain-ui";

export default function CorrectionEvidencePicker({ applicationId, noticeId, itemId }: {
  applicationId: string; noticeId: string; itemId: string;
}) {
  const { data, execute } = useWorkspace();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState("");
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  if (!data) return null;
  const application = data.applications.find(row => row.id === applicationId);
  const item = data.deficiencies.find(row => row.id === noticeId)?.items.find(row => row.id === itemId);
  if (!application || !item) return null;
  const original = data.documents.find(row => row.id === item.documentId);
  const target = original && (!original.applicationId || original.applicationId === application.id) ? original : undefined;
  const kinds = [...new Set([...data.configurations.filter(row => row.category === "DOCUMENT_TYPE").map(row => String(row.values.code ?? "").replace(/^DEMO-/, "")), ...data.documents.map(row => row.type)])].filter(Boolean);
  const documentType = original?.type || type;
  const options = compatibleEvidence(data, application, item);
  async function upload() {
    if (!file || !application) return;
    setError(""); setSaved("");
    if (!documentType) { setError("Choose the document type before uploading."); return; }
    if (file.size > 10 * 1024 * 1024 || !["application/pdf", "image/png", "image/jpeg"].includes(file.type)) {
      setError("Choose a PDF, PNG or JPEG within 10 MB."); return;
    }
    setBusy(true);
    try {
      const versionId = crypto.randomUUID();
      await putFile(versionId, file);
      const result = await execute({kind:"document.save", id:target?.id, values:{
        institutionId:application.institutionId, applicationId:target?.applicationId || application.id,
        type:documentType, versionId, fileName:file.name, mimeType:file.type, sizeBytes:file.size,
        issuer:target?.issuer || "", reference:target?.reference || "",
      }});
      const document = result.data.documents.find(row => row.id === result.id);
      if (!document?.currentVersionId) throw new Error("The upload was saved; refresh the evidence list to select its version.");
      setSelected(document.currentVersionId);
      setSaved(`${file.name} uploaded and selected. Human verification remains pending.`);
      setFile(null);
      if (input.current) input.current.value = "";
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Upload failed. Choose the file and try again."); }
    finally { setBusy(false); }
  }
  return <>
    <label className={s.field}>Exact correction evidence version
      <select name={`evidence-${item.id}`} value={selected} onChange={event => setSelected(event.target.value)} required={Boolean(item.documentId)}>
        <option value="">Choose an uploaded version…</option>
        {options.map(({document, version}) => <option key={version.id} value={version.id}>{humanize(document.type)} · v{version.number} · {version.fileName} · {humanize(version.verification)}</option>)}
      </select>
    </label>
    {!options.length && <p>No compatible evidence version is uploaded for this application yet.</p>}
    <input ref={input} type="file" hidden accept="application/pdf,image/png,image/jpeg" aria-label={`Choose local correction file for ${item.criterion || item.id}`} onChange={event => {setFile(event.target.files?.[0] ?? null); setError(""); setSaved("");}} />
    <button type="button" className={s.button} disabled={busy} onClick={() => input.current?.click()}>Upload correction evidence</button>
    {file && <div className={s.item}>
      <p>Selected local file: {file.name}</p>
      {original ? <p>Document type: {humanize(original.type)}</p> : <label className={s.field}>Document type<select value={type} onChange={event => setType(event.target.value)}><option value="">Choose…</option>{kinds.map(kind => <option key={kind} value={kind}>{humanize(kind)}</option>)}</select></label>}
      <button type="button" className={s.button} disabled={busy} onClick={() => void upload()}>{busy ? "Uploading…" : "Upload and attach selected file"}</button>
    </div>}
    {error && <p role="alert" className={s.error}>{error}</p>}
    {saved && <p role="status" className={s.success}>{saved}</p>}
  </>;
}
