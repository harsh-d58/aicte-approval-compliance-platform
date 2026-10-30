/* Isolated static build: original live routes/config remain untouched. */
const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const stage=path.join(root,'.static-demo');
if(path.dirname(stage)!==root)throw new Error('Invalid static stage path');
fs.mkdirSync(stage,{recursive:true});
// Only known source paths are copied; never copy .env, storage or credentials.
for(const name of ['app','lib','public']) {
 const destination=path.join(stage,name);
 fs.rmSync(destination,{recursive:true,force:true});
 fs.cpSync(path.join(root,name),destination,{recursive:true});
}
for(const name of ['package.json','package-lock.json','tsconfig.json','postcss.config.mjs'])if(fs.existsSync(path.join(root,name)))fs.copyFileSync(path.join(root,name),path.join(stage,name));
const dependencies=path.join(stage,'node_modules');
if(!fs.existsSync(dependencies))fs.symlinkSync(path.join(root,'node_modules'),dependencies,process.platform==='win32'?'junction':'dir');
function walk(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(dir,entry.name)):[path.join(dir,entry.name)]);}
for(const file of [...walk(path.join(stage,'app')),...walk(path.join(stage,'lib'))]) {
 if(!/\.tsx?$/.test(file)||file.startsWith(path.join(stage,'lib','static')))continue;
 let source=fs.readFileSync(file,'utf8').replace(/from (["'])next\/link\1/g,'from "@/lib/static/navigation"').replace(/from (["'])next\/navigation\1/g,'from "@/lib/static/navigation"');
 if(path.basename(file)==='page.tsx'&&file.includes('[')){
   const keys=[...path.relative(path.join(stage,'app'),file).matchAll(/\[([^\]]+)\]/g)].map(match=>match[1]);
   const params=Object.fromEntries(keys.map(key=>[key,'item']));
   const client=path.join(path.dirname(file),'StaticRecordScreen.tsx');
   fs.writeFileSync(client,source);
   source='import Screen from "./StaticRecordScreen";\nexport const dynamicParams=false;\nexport function generateStaticParams(){return '+JSON.stringify([params])+';}\nexport default function Page(){return <Screen/>;}\n';
 }
 fs.writeFileSync(file,source);
}
// Legacy/new-ID direct links enter this static shell and canonicalize before use.
const open=path.join(stage,'app','(workspace)','portal','open');fs.mkdirSync(open,{recursive:true});
fs.writeFileSync(path.join(open,'page.tsx'),'"use client";\nimport {useEffect} from "react";import {staticHref} from "@/lib/static/routes";export default function Open(){useEffect(()=>{const current=location.pathname+location.search+location.hash;const next=staticHref(current);location.replace(next!==current?next:"/portal/");},[]);return <p>Opening demo record…</p>;}');
fs.writeFileSync(path.join(stage,'next.config.ts'),'import type {NextConfig} from "next";import path from "node:path";const config:NextConfig={output:"export",trailingSlash:true,images:{unoptimized:true},turbopack:{root:path.resolve(process.cwd(),"..")}};export default config;');
const {loadEnvConfig}=require(path.join(root,'node_modules','@next','env'));
loadEnvConfig(path.resolve(root,'..'));
const env={...process.env,NEXT_PUBLIC_PORTAL_MODE:'demo',NEXT_TELEMETRY_DISABLED:'1'};
env.NEXT_PUBLIC_SUPABASE_URL ||= env.SUPABASE_URL || '';
const result=spawnSync(process.execPath,[path.join(root,'node_modules','next','dist','bin','next'),'build','--webpack'],{cwd:stage,env,stdio:'inherit'});
if(result.status!==0)process.exit(result.status||1);
const out=path.resolve(root,'out');if(path.dirname(out)!==root)throw new Error('Invalid static output path');fs.rmSync(out,{recursive:true,force:true});fs.cpSync(path.join(stage,'out'),out,{recursive:true});
console.log('Static demo exported to frontend/out. No Node or Python server is required.');
