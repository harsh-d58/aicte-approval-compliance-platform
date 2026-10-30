import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";
import * as jsxRuntime from "react/jsx-runtime";
import { renderToStaticMarkup } from "react-dom/server";

function load(relative, dependencies = {}) {
  const source = ts.transpileModule(readFileSync(fileURLToPath(new URL(relative, import.meta.url)), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const module = { exports: {} };
  new Function("module", "exports", "require", source)(module, module.exports, name => {
    if (Object.hasOwn(dependencies, name)) return dependencies[name];
    throw new Error(`Unexpected dependency ${name}`);
  });
  return module.exports;
}
const models = load("../lib/portal/view-models.ts");
const { default: AuditVerification, verificationHeadline } = load("../app/portal-ui/AuditVerification.tsx", {
  "react/jsx-runtime": jsxRuntime,
  "@/lib/portal/view-models": models,
  "./AuditVerification.module.css": { default: {} },
});
const result = {
  valid: true, simulation: false, simulated_event_id: null, total_events: 600,
  genesis_hash: "a".repeat(64), head_hash: "b".repeat(64), verified_at: "2026-10-30T09:00:00Z",
  errors: [], immutable_triggers_active: true, active_triggers: ["audit_no_update"],
  recent_blocks: [{ id: "event-600", action: "COMPLIANCE_EVIDENCE_SUBMITTED", actor_id: "institution-user", entity_type: "evidence_submission", entity_id: "submission-1", event_at: "2026-10-30T08:59:00Z", previous_hash: "a".repeat(64), event_hash: "b".repeat(64), valid: true }],
};
const html = value => renderToStaticMarkup(jsxRuntime.jsx(AuditVerification, {result:value, actorNames:{"institution-user":"Ananya Rao"}}));

test("real successful chain uses the exact Phase11 success wording and readable event evidence", () => {
  const markup = html(result);
  assert.equal(verificationHeadline(result), "SUCCESS: Cryptographic hash chain intact and mathematically valid");
  for (const text of ["Events checked", "Integrity findings", "Verified at (IST)", "Recent verified events", "Ananya Rao", "Compliance evidence submitted", "submission-1", "Inspect hashes", "Showing the latest 1 of 600", result.head_hash]) assert.ok(markup.includes(text), text);
  assert.ok(!markup.includes("No matching records"), "a clean chain must not render a misleading empty failure table");
});

test("simulation and genuine integrity failures can never display the real ledger success phrase", () => {
  const failure = {...result, valid:false, errors:[{id:"event-600",code:"HASH_INVALID"}], recent_blocks:[{...result.recent_blocks[0],valid:false}]};
  for (const value of [failure, {...failure,simulation:true,simulated_event_id:"event-600"}, {...result,simulation:true}, {...result,errors:failure.errors}]) assert.ok(!html(value).includes("SUCCESS: Cryptographic hash chain intact"));
  assert.match(html(failure), /Stored content no longer matches its SHA-256 digest/);
  assert.match(html({...failure,simulation:true}), /Tamper detected in the simulated copy/);
  assert.match(html({...failure,simulation:true}), /stored ledger was not changed/);
});

test("database protection and missing fingerprints remain honest independent of chain validity", () => {
  const markup = html({...result, immutable_triggers_active:false, active_triggers:[], recent_blocks:[{...result.recent_blocks[0],event_hash:null,previous_hash:null,valid:false}]});
  assert.match(markup,/Immutability trigger not confirmed/);
  assert.match(markup,/Missing digest/);
  assert.match(markup,/Genesis \/ no predecessor/);
});
