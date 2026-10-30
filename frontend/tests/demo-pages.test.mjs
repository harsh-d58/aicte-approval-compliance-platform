import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {test} from "node:test";
import ts from "typescript";
import * as jsx from "react/jsx-runtime";

const root=fileURLToPath(new URL("../",import.meta.url));
function load(file,deps){const source=ts.transpileModule(readFileSync(resolve(root,file),"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;const module={exports:{}};new Function("module","exports","require",source)(module,module.exports,name=>{if(Object.hasOwn(deps,name))return deps[name];throw Error(name);});return module.exports;}
function find(tree,p){if(tree==null||typeof tree!=="object")return[];if(Array.isArray(tree))return tree.flatMap(t=>find(t,p));return[...(p(tree)?[tree]:[]),...find(tree.props?.children,p)];}
function hooks(){const values=[];let cursor=0;return{start(){cursor=0;},react:{useEffect(){},useState(initial){const i=cursor++;if(!(i in values))values[i]=initial;return[values[i],v=>{values[i]=typeof v==="function"?v(values[i]):v;}];}}};}

test("arbitrary local OCR file is never represented as recognized text and saves only an explicit simulation",async()=>{
 const h=hooks();const commands=[];const extracted=[];const navigated=[];
 const {default:Studio}=load("app/portal-ui/DemoOcrTester.tsx",{react:h.react,"react/jsx-runtime":jsx,"./domain-ui":{s:{},Table:()=>null,useWorkspace:()=>({execute:async command=>{commands.push(command);return{id:"check-new"};},router:{push:path=>navigated.push(path)}})}});
 const render=()=>{h.start();return Studio({documentId:"doc-a",versionId:"ver-a",onExtractionComplete:value=>extracted.push(value)});};
 let tree=render();const input=find(tree,t=>t.type==="input"&&t.props.type==="file")[0];
 const file=new File(["%PDF-1.4 fake document bytes"],"unknown.pdf",{type:"application/pdf"});
 input.props.onChange({target:{files:[file]}});tree=render();
 await find(tree,t=>t.type==="button"&&t.props.children==="Run extraction simulation")[0].props.onClick();
 await new Promise(resolve=>setImmediate(resolve));tree=render();
 assert.equal(extracted.length,1);assert.equal(extracted[0].confidence_summary.ocr_performed,false);
 assert.equal(extracted[0].source_text,null);assert.equal(extracted[0].extracted_fields.certificate_number,null);
 assert.equal(extracted[0].confidence_summary.overall_confidence,null);assert.match(extracted[0].confidence_summary.source_sha256,/^[a-f0-9]{64}$/);
 await find(tree,t=>t.type==="button"&&t.props.children==="Save simulated document check")[0].props.onClick();
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(commands[0].kind,"document.check");assert.equal(commands[0].values.versionId,"ver-a");assert.match(commands[0].values.reason,/no OCR service contacted/);
 assert.deepEqual(navigated,["/portal/documents/doc-a/checks/check-new"]);
});

test("demo report generation freezes the exact filtered rows without using a live download",async()=>{
 const h=hooks();const commands=[];const navigated=[];let liveCalls=0;
 const data={users:[{id:"user-r",assignments:[{role:"REGIONAL",scope:{type:"REGION",id:"r1"}}]}],applications:[],institutions:[],regions:[],visits:[],slots:[],conditions:[],documents:[],tasks:[],notifications:[],reportRuns:[],reportDefinitions:[{id:"application-pendency",name:"Pendency",columns:["Application"]}]};
 const workspace={data,allData:data,user:data.users[0],assignmentIndex:0,params:{reportCode:"application-pendency"},router:{push:path=>navigated.push(path)},execute:async command=>{commands.push(command);return{id:"run-new"};}};
 const {default:Reports}=load("app/portal-ui/ReportPages.tsx",{react:h.react,"react/jsx-runtime":jsx,"./LiveProvider":{useLive:()=>({download(){liveCalls++;throw Error("Live API forbidden");}})},"next/navigation":{useSearchParams:()=>new URLSearchParams()},"./domain-ui":{useWorkspace:()=>workspace,Page:()=>null,Panel:()=>null,Links:()=>null,Table:()=>null,Unavailable:()=>null,Meta:()=>null,Link:()=>null,Badge:()=>null,s:{},formatDateTime:v=>v},"@/lib/portal/report-rows":{getReportRows:()=>[{Application:"A-1"},{Application:"A-2"}]},"@/lib/portal/exports":{csv(){},xlsx(){},pdf(){}},"@/lib/portal/files":{download(){}},"@/lib/portal/view-models":{demoNow:"2026-10-30",scopeName:()=>"North"},"@/lib/portal/mode":{isDemoMode:true}});
 h.start();const tree=Reports({mode:"detail"});
 await find(tree,t=>t.type==="button"&&t.props.children==="Generate export snapshot")[0].props.onClick();
 assert.equal(commands[0].kind,"report.create");assert.equal(commands[1].kind,"report.complete");assert.deepEqual(commands[1].values.rows,[{Application:"A-1"},{Application:"A-2"}]);
 assert.equal(liveCalls,0);assert.deepEqual(navigated,["/portal/report-runs/run-new"]);
});
