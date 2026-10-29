"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useLive } from "./LiveProvider";
import { scopedSnapshot, setPortalNow } from "@/lib/portal/view-models";
import type { PortalCollections, User } from "@/lib/portal/types";
import type { Command, CommandResult } from "@/lib/portal/commands";
import { executeLiveCommand } from "@/lib/live/commands";
type DemoContext = {
 allData: PortalCollections | null; data: PortalCollections | null; user: User | null;
 assignmentIndex: number; loading: boolean; error: string; notice: string; signedOut: boolean;
 refreshedAt: string | null; refreshing: boolean;
 signIn: (id: string) => Promise<void>; selectScope: (index: number) => void; signOut: () => void;
 reload: () => void; markNotification: (id: string, read: boolean) => Promise<void>;
 execute: (command: Command) => Promise<CommandResult>; clearNotice: () => void;
};
const Context = createContext<DemoContext | null>(null);
/** Existing page context backed entirely by PostgreSQL, including demo personas. */
export function DemoProvider({ children }: { children: React.ReactNode }) {
 const live = useLive(); const { identity, get } = live;
 const [allData, setAllData] = useState<PortalCollections | null>(null);
 const currentData = useRef<PortalCollections | null>(null);
 const subject = useRef<string | null>(null); subject.current = identity?.user.id ?? null;
 const [assignmentIndex, setAssignmentIndex] = useState(0);
 const [loading, setLoading] = useState(true);
 const [refreshing, setRefreshing] = useState(false);
 const [error, setError] = useState(""); const [notice, setNotice] = useState("");
 const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
 const sequence = useRef(0);
 const refresh = useCallback(async () => {
   const actor = subject.current; if (!actor) return null;
   const request = ++sequence.current; setRefreshing(true);
   try {
     const snapshot = await get<PortalCollections>("/portal/snapshot");
     if (subject.current !== actor) return null;
     setPortalNow(new Date().toISOString()); currentData.current = snapshot; setAllData(snapshot); setError(""); setRefreshedAt(new Date().toISOString()); return snapshot;
   } catch (cause) {
     if (subject.current === actor) setError(cause instanceof Error ? cause.message : "Unable to fetch database records.");
     throw cause;
   } finally { if (request === sequence.current) { setLoading(false); setRefreshing(false); } }
 }, [get]);
 useEffect(() => {
   sequence.current++; currentData.current = null; setAllData(null); setAssignmentIndex(0); setError(""); setRefreshedAt(null);
   if (!identity) { setLoading(live.loading); return; }
   setLoading(true); void refresh().catch(() => {});
   const timer = window.setInterval(() => { if (document.visibilityState === "visible") void refresh().catch(() => {}); }, 30_000);
   const focus = () => { void refresh().catch(() => {}); }; window.addEventListener("focus", focus);
   return () => { clearInterval(timer); window.removeEventListener("focus", focus); };
 }, [identity, live.loading, refresh]);
 const user = allData?.users.find(u => u.id === identity?.user.id && u.status === "ACTIVE") ?? null;
 const index = user?.assignments[assignmentIndex] ? assignmentIndex : 0;
 const data = useMemo(() => allData && user?.assignments[index] ? scopedSnapshot(allData, user, index) : null, [allData, user, index]);
 const execute = async (command: Command): Promise<CommandResult> => {
   const before = currentData.current; const actor = subject.current;
   if (!before || !actor) throw new Error("Choose a workspace first.");
   const result = await executeLiveCommand(command, before, live);
   if (subject.current !== actor) throw new Error("Your identity changed. Reopen the workspace to inspect the saved result.");
   const saved = await refresh(); const current = saved ?? currentData.current; if (!current) throw new Error("The action was saved; refresh to see its result.");
   setNotice(result.message); return { ...result, data: current };
 };
 const markNotification = async (id: string, read: boolean) => {
   try { await execute({kind: "notification.read", id, values: {read}}); }
   catch (cause) { setNotice(cause instanceof Error ? cause.message : "Notification update failed."); }
 };
 return <Context.Provider value={{allData, data, user, assignmentIndex:index, loading:loading || live.loading, error, notice,
   signedOut:!identity, refreshedAt, refreshing, signIn:live.signInDemo, selectScope:setAssignmentIndex,
   signOut:() => {sequence.current++; currentData.current=null; setAllData(null); void live.signOut();},
   reload:() => {void refresh().catch(() => {});}, markNotification, execute, clearNotice:() => setNotice("")}}>{children}</Context.Provider>;
}
export function useDemo() { const value=useContext(Context); if (!value) throw new Error("DemoProvider is required"); return value; }
