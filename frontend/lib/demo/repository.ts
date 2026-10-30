import { applyCommand, type Command, type CommandResult } from "../portal/commands";
import { mockData, mockMeta } from "../portal/mock-data";
import { setPortalNow } from "../portal/view-models";
import type { AuditEvent, PortalCollections } from "../portal/types";

type RecordState = { schema: 1; revision: number; data: PortalCollections };
const DATABASE = "setu-browser-demo-v1";
const STORE = "state";
const KEY = "shared-demo";
const CHANNEL = "setu-demo-changed";
let channel: BroadcastChannel | undefined;
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach(listener => listener());
  channel?.postMessage("changed");
}
function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") { reject(new Error("Browser storage is unavailable. Enable site storage to use this demo.")); return; }
    const request = indexedDB.open(DATABASE, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error("Demo storage could not open."));
  });
}
async function read(): Promise<RecordState | undefined> {
  const db = await open();
  try { return await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly"); const request = tx.objectStore(STORE).get(KEY);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error("Demo data could not load."));
  }); } finally { db.close(); }
}
async function compareAndSave(previous: number | undefined, next: RecordState): Promise<boolean> {
  const db = await open();
  try { return await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite"); const store = tx.objectStore(STORE);
    let changed = false;
    const request = store.get(KEY);
    request.onsuccess = () => { if (request.result?.revision === previous) { store.put(next, KEY); changed = true; } };
    tx.oncomplete = () => resolve(changed);
    tx.onerror = () => reject(new Error("Demo changes could not be saved. Check browser storage space."));
    tx.onabort = () => reject(new Error("Demo save was interrupted. No success was recorded."));
  }); } finally { db.close(); }
}
export async function eventHash(event: AuditEvent): Promise<string> {
  const { eventHash: _hash, anchor: _anchor, ...payload } = event;
  const canonical = Object.fromEntries(Object.entries(payload).sort(([a], [b]) => a.localeCompare(b)));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(canonical)));
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, "0")).join("");
}
async function initial(): Promise<RecordState> {
  const data = structuredClone(mockData);
  let previousHash: string | null = null;
  for (const event of data.auditEvents) {
    event.previousHash = previousHash; event.anchor = "DISABLED";
    event.eventHash = await eventHash(event); previousHash = event.eventHash;
  }
  return { schema: 1, revision: 1, data };
}
async function state(): Promise<RecordState> {
  let record = await read();
  if (!record) { const seed = await initial(); await compareAndSave(undefined, seed); record = await read(); }
  if (!record || record.schema !== 1) throw new Error("This demo dataset needs migration. Export or reset it before continuing.");
  setPortalNow(mockMeta.now);
  return record;
}

export const demoRepository = {
  async snapshot(): Promise<PortalCollections> { return structuredClone((await state()).data); },
  async execute(command: Command, actorId: string, index: number): Promise<CommandResult> {
    if (command.kind === "document.save") {
      const { getFile } = await import("../portal/files");
      const values = command.values ?? {};
      const blob = await getFile(String(values.versionId ?? ""));
      if (!blob || blob.size !== Number(values.sizeBytes) || blob.type !== values.mimeType) {
        throw new Error("Choose the file again. Saved bytes must match this document version.");
      }
    }
    // Each IndexedDB write compares the revision inside one transaction. This
    // also protects browsers without navigator.locks from cross-tab lost writes.
    for (let attempt = 0; attempt < 5; attempt++) {
      const previous = await state();
      const actor = previous.data.users.find(user => user.id === actorId);
      if (!actor) throw new Error("Choose a demo persona first.");
      const result = applyCommand(previous.data, actor, index, command);
      for (const event of result.data.auditEvents.slice(previous.data.auditEvents.length)) {
        const position = result.data.auditEvents.indexOf(event);
        event.previousHash = result.data.auditEvents[position - 1]?.eventHash ?? null;
        event.eventHash = await eventHash(event);
      }
      if (await compareAndSave(previous.revision, { schema: 1, revision: previous.revision + 1, data: result.data })) {
        notify(); return { ...result, message: result.message + " Saved in this browser only." };
      }
    }
    throw new Error("Another tab changed this demo. Reload before submitting again.");
  },
  async reset() {
    const current = await state(); const seed = await initial(); seed.revision = current.revision + 1;
    if (!await compareAndSave(current.revision, seed)) throw new Error("Another tab changed the demo. Retry reset.");
    notify(); return structuredClone(seed.data);
  },
  subscribe(listener: () => void) {
    listeners.add(listener);
    if (!channel && typeof BroadcastChannel !== "undefined") {
      channel = new BroadcastChannel(CHANNEL);
      channel.onmessage = () => listeners.forEach(callback => callback());
    }
    return () => { listeners.delete(listener); if (!listeners.size) { channel?.close(); channel = undefined; } };
  },
  async verifyAudit(simulate = false) {
    const data = await this.snapshot(); const events = data.auditEvents;
    const target = simulate ? events.at(-1) : undefined;
    if (target) target.reason += " [in-memory simulated alteration]";
    const errors: { id: string; code: string }[] = [];
    let previousHash: string | null = null;
    for (const event of events) {
      if (event.previousHash !== previousHash) errors.push({ id: event.id, code: "PREDECESSOR_INVALID" });
      if (await eventHash(event) !== event.eventHash) errors.push({ id: event.id, code: "HASH_INVALID" });
      previousHash = event.eventHash;
    }
    return { valid: errors.length === 0, simulation: simulate, simulated_event_id: target?.id ?? null,
      local_demo: true, total_events: events.length, genesis_hash: events[0]?.eventHash ?? null,
      head_hash: events.at(-1)?.eventHash ?? null, verified_at: new Date().toISOString(), errors,
      immutable_triggers_active: false, active_triggers: [],
      recent_blocks: events.slice(-8).map(event => ({ id: event.id, action: event.action, actor_id: event.actorId,
        entity_type: event.entityType, entity_id: event.entityId, event_at: event.at,
        previous_hash: event.previousHash, event_hash: event.eventHash, valid: !errors.some(error => error.id === event.id) })) };
  },
};
