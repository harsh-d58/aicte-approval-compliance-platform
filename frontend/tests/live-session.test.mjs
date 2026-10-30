import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import ts from "typescript";
import * as jsxRuntime from "react/jsx-runtime";

const root = fileURLToPath(new URL("../", import.meta.url));
const storageKey = "aicte.live.session.v1";
const session = (token, refresh = "prototype", expires = Date.now() + 3_600_000) => ({ access_token: token, refresh_token: refresh, expires_at: expires });
const profile = id => ({ user: { id, display_name: id }, assignments: [] });
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function load(file, dependencies) {
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

// Run actual provider functions with persistent hook slots, stable callbacks,
// dependency-aware effects and effect cleanup. Deferred API promises control the
// race ordering rather than relying on sleeps or implementation-string checks.
function hooks() {
  const slots = [];
  let cursor = 0, effects = [], dirty = false, component, tree;
  const same = (before, after) => before && after && before.length === after.length && after.every((value, i) => Object.is(value, before[i]));
  const react = {
    createContext: () => ({ Provider: Symbol("Provider") }),
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useState(initial) {
      const i = cursor++;
      slots[i] ??= { value: typeof initial === "function" ? initial() : initial };
      return [slots[i].value, next => {
        const value = typeof next === "function" ? next(slots[i].value) : next;
        if (!Object.is(value, slots[i].value)) { slots[i].value = value; dirty = true; }
      }];
    },
    useCallback(callback, dependencies) {
      const i = cursor++;
      if (!same(slots[i]?.dependencies, dependencies)) slots[i] = { dependencies, value: callback };
      return slots[i].value;
    },
    useMemo(factory, dependencies) {
      const i = cursor++;
      if (!same(slots[i]?.dependencies, dependencies)) slots[i] = { dependencies, value: factory() };
      return slots[i].value;
    },
    useEffect(effect, dependencies) {
      const i = cursor++;
      if (!same(slots[i]?.dependencies, dependencies)) {
        const previous = slots[i];
        slots[i] = { dependencies, cleanup: previous?.cleanup };
        effects.push(() => { previous?.cleanup?.(); slots[i].cleanup = effect(); });
      }
    },
  };
  const render = () => {
    cursor = 0; effects = []; dirty = false;
    tree = component({ children: null });
    for (const effect of effects) effect();
  };
  return {
    react,
    mount(value) { component = value; render(); },
    get value() { return tree.props.value; },
    async flush() { for (let i = 0; i < 40; i++) { await Promise.resolve(); if (dirty) render(); } },
    unmount() { for (const slot of slots) slot?.cleanup?.(); },
  };
}
async function environment(run) {
  const previous = Object.fromEntries(["sessionStorage", "window", "document", "clearInterval"].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const store = new Map(), listeners = new Map(), intervals = new Map();
  let interval = 0;
  globalThis.sessionStorage = { getItem: key => store.get(key) ?? null, setItem: (key, value) => store.set(key, value), removeItem: key => store.delete(key) };
  globalThis.window = {
    setInterval(callback) { const id = ++interval; intervals.set(id, callback); return id; },
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: (name, callback) => { if (listeners.get(name) === callback) listeners.delete(name); },
  };
  globalThis.document = { visibilityState: "visible" };
  globalThis.clearInterval = id => intervals.delete(id);
  try { await run({ store, listeners, intervals }); }
  finally {
    for (const [key, descriptor] of Object.entries(previous)) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  }
}
function liveProvider(harness, overrides) {
  const client = {
    liveConfig: { supabaseUrl: "https://synthetic.invalid", supabaseKey: "synthetic-key" },
    apiGet: async () => profile("actor"), refreshSession: async () => session("refreshed", "refresh"),
    signInWithPersona: async () => session("new-demo"), signInWithPassword: async () => session("new-live", "refresh"),
    signOutSession: async () => {}, ...overrides,
  };
  return load("app/portal-ui/LiveProvider.tsx", { react: harness.react, "react/jsx-runtime": jsxRuntime, "@/lib/live/client": client, "@/lib/portal/mode": {isDemoMode:false} }).LiveProvider;
}

test("a failed old restore cannot erase a newer successful demo sign-in", async () => environment(async ({ store }) => {
  store.set(storageKey, JSON.stringify(session("old-demo")));
  const oldProfile = deferred(), harness = hooks();
  harness.mount(liveProvider(harness, {
    apiGet: async (_path, token) => token === "old-demo" ? oldProfile.promise : profile("new-persona"),
  }));
  await harness.flush();
  await harness.value.signInDemo("user-regional");
  await harness.flush();
  assert.equal(harness.value.identity.user.id, "new-persona");
  oldProfile.reject(new Error("The old session expired"));
  await harness.flush();
  assert.equal(harness.value.identity.user.id, "new-persona");
  assert.equal(JSON.parse(store.get(storageKey)).access_token, "new-demo");
  assert.equal(harness.value.loading, false);
  assert.equal(harness.value.error, "");
  harness.unmount();
}));

test("signing out during pending profile validation cannot resurrect credentials or stay loading", async () => environment(async ({ store }) => {
  const pendingProfile = deferred(), harness = hooks();
  harness.mount(liveProvider(harness, { apiGet: () => pendingProfile.promise }));
  await harness.flush();
  const signIn = harness.value.signInDemo("user-regional");
  const rejected = assert.rejects(signIn, /sign-in changed/);
  await harness.flush();
  await harness.value.signOut();
  await harness.flush();
  pendingProfile.resolve(profile("late-persona"));
  await rejected;
  await harness.flush();
  assert.equal(harness.value.identity, null);
  assert.equal(store.has(storageKey), false);
  assert.equal(harness.value.loading, false, "sign-out must release initial loading even when the canceled sign-in finishes later");
  harness.unmount();
}));

test("concurrent expired-token reads share one Supabase refresh and retain its replacement", async () => environment(async ({ store }) => {
  store.set(storageKey, JSON.stringify(session("expired", "refresh-old", Date.now() - 1_000)));
  const refreshed = deferred(), calls = [], harness = hooks();
  let refreshes = 0;
  harness.mount(liveProvider(harness, {
    refreshSession: () => { refreshes++; return refreshed.promise; },
    apiGet: async (path, token) => { calls.push({ path, token }); return profile("actor"); },
  }));
  await harness.flush();
  const one = harness.value.get("/one"), two = harness.value.get("/two");
  assert.equal(refreshes, 1);
  refreshed.resolve(session("refreshed", "refresh-new"));
  await Promise.all([one, two]);
  await harness.flush();
  assert.equal(refreshes, 1);
  assert.equal(calls.length, 3, "restore and both parallel reads must complete");
  assert(calls.every(call => call.token === "refreshed"));
  assert.equal(JSON.parse(store.get(storageKey)).refresh_token, "refresh-new");
  harness.unmount();
}));

test("focus, poll and reload coalesce pending reads but a committed mutation fetches a fresh snapshot", async () => environment(async ({ listeners, intervals }) => {
  const requests = [], harness = hooks();
  const actor = { user: { id: "actor" } };
  const live = { identity: actor, loading: false, get: () => { const read = deferred(); requests.push(read); return read.promise; } };
  const { DemoProvider } = load("app/portal-ui/DemoProvider.tsx", {
    react: harness.react, "react/jsx-runtime": jsxRuntime,
    "@/lib/portal/mode": {isDemoMode:false}, "next/navigation": { usePathname: () => "/portal" }, "./LiveProvider": { useLive: () => live },
    "@/lib/portal/view-models": { scopedSnapshot: value => value, setPortalNow() {} },
    "@/lib/live/commands": { executeLiveCommand: async () => ({ message: "Saved" }) },
    "@/lib/live/workspace-scope": { workspaceAssignmentIndex: () => 0 },
  });
  const snapshot = marker => ({ marker, users: [{ id: "actor", status: "ACTIVE", assignments: [{ role: "REGIONAL" }] }] });
  harness.mount(DemoProvider);
  await harness.flush();
  listeners.get("focus")(); listeners.get("focus")();
  for (const callback of intervals.values()) callback();
  harness.value.reload();
  await harness.flush();
  assert.equal(requests.length, 1);
  requests[0].resolve(snapshot("initial"));
  await harness.flush();
  assert.equal(harness.value.allData.marker, "initial");
  listeners.get("focus")();
  await harness.flush();
  assert.equal(requests.length, 2);
  const action = harness.value.execute({ kind: "notification.read", id: "synthetic" });
  await harness.flush();
  assert.equal(requests.length, 3, "post-write refresh must not reuse a request made before the write");
  requests[2].resolve(snapshot("after-write"));
  const result = await action;
  await harness.flush();
  assert.equal(result.data.marker, "after-write");
  requests[1].resolve(snapshot("stale-before-write"));
  await harness.flush();
  assert.equal(harness.value.allData.marker, "after-write", "late pre-write reads cannot overwrite the committed view");
  listeners.get("focus")();
  await harness.flush();
  const secondAction = harness.value.execute({ kind: "notification.read", id: "synthetic-second" });
  await harness.flush();
  requests[4].resolve(snapshot("after-second-write"));
  await secondAction;
  await harness.flush();
  requests[3].reject(new Error("An obsolete background read timed out"));
  await harness.flush();
  assert.equal(harness.value.allData.marker, "after-second-write");
  assert.equal(harness.value.error, "", "a failed obsolete read must not hide a newer successfully loaded workspace");
  harness.unmount();
}));

test("identity and workspace request timeouts return actionable errors instead of waiting forever", async () => {
  const previous = { fetch: globalThis.fetch, setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout };
  const timeouts = [];
  globalThis.setTimeout = (callback, delay) => { timeouts.push(delay); queueMicrotask(callback); return 1; };
  globalThis.clearTimeout = () => {};
  globalThis.fetch = (_url, init) => new Promise((_resolve, reject) => {
    const abort = () => reject(new DOMException("aborted", "AbortError"));
    if (init.signal.aborted) abort();
    else init.signal.addEventListener("abort", abort, { once: true });
  });
  try {
    const client = load("lib/live/client.ts", {});
    await assert.rejects(client.apiGet("/me", "synthetic"), /account could not load in time.*Sign in again/);
    await assert.rejects(client.apiGet("/portal/snapshot", "synthetic"), /workspace took too long.*Try again/);
    await assert.rejects(client.signInWithPersona("user-regional"), /Demo sign-in timed out/);
    await assert.rejects(client.signInWithPassword("synthetic@example.invalid", "synthetic"), /Supabase sign-in timed out/);
    assert.deepEqual(timeouts, [20_000, 45_000, 20_000, 20_000]);
    globalThis.fetch = async (_url, init) => ({
      ok: true,
      json: () => new Promise((_resolve, reject) => {
        const abort = () => reject(new DOMException("body aborted", "AbortError"));
        if (init.signal.aborted) abort();
        else init.signal.addEventListener("abort", abort, { once: true });
      }),
    });
    await assert.rejects(client.apiGet("/portal/snapshot", "synthetic"), /workspace took too long.*Try again/, "headers alone cannot cancel the timeout for a stalled response body");
  } finally { Object.assign(globalThis, previous); }
});
