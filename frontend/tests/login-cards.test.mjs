import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";
import * as jsxRuntime from "react/jsx-runtime";

const root = fileURLToPath(new URL("../", import.meta.url));
function load(file, dependencies = {}) {
  const source = ts.transpileModule(readFileSync(resolve(root, file), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const module = { exports: {} };
  new Function("module", "exports", "require", source)(module, module.exports, name => {
    if (Object.hasOwn(dependencies, name)) return dependencies[name];
    throw new Error(`Unexpected dependency ${name}`);
  });
  return module.exports;
}
const models = load("lib/portal/view-models.ts");
const roles = ["INSTITUTION", "SCRUTINY", "REGIONAL", "EVC_COORDINATOR", "EVC_EXPERT", "COMPLIANCE", "CENTRAL", "POLICY", "AUDITOR", "SYSTEM"];
function find(tree, predicate) {
  if (tree == null || typeof tree !== "object") return [];
  if (Array.isArray(tree)) return tree.flatMap(child => find(child, predicate));
  return [...(predicate(tree) ? [tree] : []), ...find(tree.props?.children, predicate)];
}

test("expired-session errors keep all cards usable and retries use stable persona keys after a broad user directory", async () => {
  const values = [];
  let cursor = 0;
  const useState = initial => {
    const slot = cursor++;
    if (!(slot in values)) values[slot] = initial;
    return [values[slot], value => { values[slot] = typeof value === "function" ? value(values[slot]) : value; }];
  };
  const requested = [];
  const destinations = [];
  const context = {
    error: "Your session expired. Sign in again.", user: null, reload() {},
    allData: { users: roles.map((role, i) => ({ id: `database-user-uuid-${i}`, displayName: role, assignments: [{ role }] })) },
    async signIn(key) {
      requested.push(key);
      if (requested.length === 1) throw new Error("Temporary connection failure");
    },
  };
  const { default: LoginPage } = load("app/(workspace)/login/page.tsx", {
    "@/lib/portal/mode": {isDemoMode:true}, react: { useState }, "react/jsx-runtime": jsxRuntime,
    "next/image": { default: () => null }, "next/link": { default: () => null },
    "next/navigation": { useRouter: () => ({ push: value => destinations.push(value) }) },
    "@/app/components/Icon": { default: () => null },
    "@/lib/portal/view-models": models,
    "@/app/portal-ui/DemoProvider": { useDemo: () => context },
    "@/app/portal-ui/LiveProvider": { useLive: () => ({}) },
    "@/app/portal-ui/ui": { Arrow: () => null, Brand: () => null },
    "@/app/portal-ui/portal.module.css": { default: {} },
  });
  const render = () => { cursor = 0; return LoginPage(); };
  const cards = tree => find(tree, node => node.type === "button" && Object.hasOwn(node.props, "aria-pressed"));
  const enter = tree => find(tree, node => node.type === "button" && node.props.children?.[0] === "Enter demonstration portal")[0];
  const previousWindow = globalThis.window;
  globalThis.window = { location: { search: "?returnTo=%2Fportal%2Fapplications" } };
  try {
    let tree = render();
    assert.equal(cards(tree).length, 10);
    cards(tree)[2].props.onClick();
    tree = render();
    await enter(tree).props.onClick();
    tree = render();
    assert.equal(cards(tree).length, 10, "a failed sign-in must not hide the cards");
    assert.equal(enter(tree).props.disabled, false, "a failed attempt must release the sign-in button");
    await enter(tree).props.onClick();
    assert.deepEqual(requested, ["user-regional", "user-regional"]);
    assert.deepEqual(destinations, ["/portal/applications"]);
  } finally {
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  }
});
