"use client";
import { useEffect, useState } from "react";
import { s, useWorkspace, Table } from "./domain-ui";
import type { Props, OcrExtractionResult } from "./OcrTester";

/** No recognition service is called. Values are explicitly supplied for a demo. */
export default function DemoOcrTester({documentId,versionId,declaredIssueDate,declaredExpiryDate,onExtractionComplete,title="Document extraction simulation"}:Props) {
 const {execute,router}=useWorkspace();
 const [file,setFile]=useState<File|null>(null);
 const [preview,setPreview]=useState("");
 const [sample,setSample]=useState(false);
 const [reference,setReference]=useState("");
 const [issuer,setIssuer]=useState("");
 const [issued,setIssued]=useState(declaredIssueDate??"");
 const [expiry,setExpiry]=useState(declaredExpiryDate??"");
 const [result,setResult]=useState<OcrExtractionResult|null>(null);
 const [error,setError]=useState("");const [busy,setBusy]=useState(false);
 useEffect(()=>{if(!file){setPreview("");return;}const url=URL.createObjectURL(file);setPreview(url);return()=>URL.revokeObjectURL(url);},[file]);
 function select(selected:File){
  setError("");setResult(null);setSample(false);setReference("");setIssuer("");
  if(!["application/pdf","image/png","image/jpeg"].includes(selected.type)||selected.size>15*1024*1024){setError("Choose a PDF, PNG or JPEG within 15 MB.");return;}
  setFile(selected);
 }
 function loadSample(){
  const text='<svg xmlns="http://www.w3.org/2000/svg" width="720" height="440"><rect width="720" height="440" fill="#f8fafc"/><text x="35" y="65" font-family="sans-serif" font-size="24">SETU DEMONSTRATION SAMPLE</text><text x="35" y="120" font-family="sans-serif" font-size="18">Reference: DEMO-SAFETY-001</text><text x="35" y="160" font-family="sans-serif" font-size="18">Issuer: Prototype authority (simulated)</text><text x="35" y="200" font-family="sans-serif" font-size="18">Issue date: 2026-01-01</text><text x="35" y="240" font-family="sans-serif" font-size="18">Expiry date: 2027-01-01</text><text x="35" y="310" font-family="sans-serif" font-size="16">Not an official certificate. No OCR or issuer verification.</text></svg>';
  setFile(new File([text],"SETU_demo_sample.svg",{type:"image/svg+xml"}));setSample(true);setResult(null);setError("");
  setReference("DEMO-SAFETY-001");setIssuer("Prototype authority (simulated)");setIssued("2026-01-01");setExpiry("2027-01-01");
 }
 async function simulate(){
  if(!file)return;setBusy(true);setError("");
  try{
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",await file.arrayBuffer())),b=>b.toString(16).padStart(2,"0")).join("");
   const next:OcrExtractionResult={status:"SIMULATED",file_name:file.name,mime_type:file.type,size_bytes:file.size,engine_name:"Browser demonstration; no OCR performed",engine_version:null,
    confidence_summary:{overall_confidence:null,source:sample?"Known synthetic sample fixture":"User-entered simulation values",ocr_performed:false,source_sha256:hash},
    extracted_fields:{certificate_number:reference||null,issuing_authority:issuer||null,extracted_issue_date:issued||null,extracted_expiry_date:expiry||null,declared_issue_date:declaredIssueDate,declared_expiry_date:declaredExpiryDate},
    source_text:sample?"Synthetic fixture: DEMO-SAFETY-001. Prototype authority. 2026-01-01 to 2027-01-01.":null,source_error:null};
   setResult(next);onExtractionComplete?.(next);
  }catch(cause){setError(cause instanceof Error?cause.message:"Simulation failed.");}finally{setBusy(false);}
 }
 async function save(){if(!documentId||!versionId)return;setBusy(true);setError("");try{
  const saved=await execute({kind:"document.check",id:documentId,values:{versionId,extracted:expiry||"Not applicable",reason:"Explicit browser extraction simulation; no OCR service contacted"}});
  router.push(`/portal/documents/${documentId}/checks/${saved.id}`);
 }catch(cause){setError(cause instanceof Error?cause.message:"Unable to save check.");}finally{setBusy(false);}}
 return <div className={s.panel}>
  <h3>{title}</h3><p className={s.note}>Demo extraction only. Uploads stay in this browser. No OCR, malware scan, issuer authentication or external service is performed.</p>
  <div className={s.actions}><input aria-label="Choose file for extraction simulation" type="file" accept="application/pdf,image/png,image/jpeg" onChange={e=>{if(e.target.files?.[0])select(e.target.files[0]);}}/><button type="button" className={s.button} onClick={loadSample}>Load demonstration sample</button></div>
  {file&&<><p>{file.name} · {Math.ceil(file.size/1024)} KB</p>{preview&&(file.type.startsWith("image/")?<img src={preview} alt="Selected local document" style={{maxWidth:"100%",maxHeight:320}}/>:<object data={preview} type={file.type} aria-label="Local document preview" style={{width:"100%",height:300}}/>)}
   <div className={s.fields}>{[["Reference",reference,setReference],["Issuer",issuer,setIssuer],["Issue date",issued,setIssued],["Expiry date",expiry,setExpiry]].map(([label,value,setter])=><label className={s.field} key={String(label)}>{String(label)}<input value={String(value)} onChange={e=>(setter as (v:string)=>void)(e.target.value)}/></label>)}</div>
   <button type="button" className={s.button} disabled={busy} onClick={()=>void simulate()}>Run extraction simulation</button></>}
  {error&&<p role="alert" className={s.error}>{error}</p>}
  {result&&<><Table columns={["Field","Simulated value","Source"]} rows={[["Reference",reference||"Not supplied",sample?"Sample fixture":"Manually supplied"],["Issuer",issuer||"Not supplied","Not authenticated"],["Issue date",issued||"Not supplied","Simulation"],["Expiry date",expiry||"Not supplied","Simulation"],["File SHA-256",result.confidence_summary.source_sha256,"Calculated from actual local bytes"]]}/><p>Recognition confidence: not measured. No text was extracted from arbitrary uploads.</p></>}
  {documentId&&versionId&&<button type="button" className={s.button} disabled={busy} onClick={()=>void save()}>Save simulated document check</button>}
 </div>;
}
