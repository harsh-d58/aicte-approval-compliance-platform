import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {test} from "node:test";
import ts from "typescript";
const source=ts.transpileModule(readFileSync(new URL('../lib/static/routes.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const module={exports:{}};new Function('module','exports',source)(module,module.exports);
const {routeMatch,staticHref}=module.exports;
test('new local IDs and nested notice IDs resolve through exported placeholder routes',()=>{
 const original='/portal/applications/application-new-random/deficiencies/notice-new?view=latest#form';
 const url=new URL(staticHref(original),'https://demo.test');
 assert.equal(url.pathname,'/portal/applications/item/deficiencies/item/');
 assert.equal(url.searchParams.get('view'),'latest');
 assert.equal(url.hash,'#form');
 assert.deepEqual(routeMatch(url.searchParams.get('__path')).params,{applicationId:'application-new-random',noticeId:'notice-new'});
 assert.equal(staticHref(url.pathname+url.search+url.hash),url.pathname+url.search+url.hash);
});
test('fixed creation/calendar pages and external links retain their destinations',()=>{
 for(const href of ['/portal/applications/new','/portal/documents/new','/portal/institutions/new','/portal/evc/calendar','/portal/admin/workflows/new','/portal/audit/verify','https://example.com/portal/evc/id']) assert.equal(staticHref(href),href);
});
