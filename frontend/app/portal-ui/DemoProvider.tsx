"use client";
import { createContext, Suspense, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useLive } from "./LiveProvider";
import { scopedSnapshot, setPortalNow } from "@/lib/portal/view-models";
import type { PortalCollections, User } from "@/lib/portal/types";
import type { Command, CommandResult } from "@/lib/portal/commands";
import { executeLiveCommand } from "@/lib/live/commands";
import { workspaceAssignmentIndex } from "@/lib/live/workspace-scope";
import { isDemoMode } from "@/lib/portal/mode";
type DemoContext = {
 allData: PortalCollections | null; data: PortalCollections | null; user: User | null;
 assignmentIndex: number; loading: boolean; error: string; notice: string; signedOut: boolean;
 refreshedAt: string | null; refreshing: boolean;
 signIn: (id: string) => Promise<void>; selectScope: (index: number) => void; signOut: () => void;
 reload: () => void; markNotification: (id: string, read: boolean) => Promise<void>;
 execute: (command: Command) => Promise<CommandResult>; clearNotice: () => void;
};
const Context = createContext<DemoContext | null>(null);
// Dynamic path reads need their own boundary during Next.js prerendering.
function WorkspaceRoute({onChange}:{onChange:(workspace:boolean)=>void}) {
 const pathname = usePathname();
 useEffect(() => onChange(pathname.startsWith("/portal")), [pathname, onChange]);
 return null;
}
/** Existing page context backed entirely by PostgreSQL, including demo personas. */
export function DemoProvider({ children }: { children: React.ReactNode }) {
 const live = useLive(); const { identity, get } = live;
 const [isWorkspace,setIsWorkspace] = useState(true);
 const [allData, setAllData] = useState<PortalCollections | null>(null);
 const currentData = useRef<PortalCollections | null>(null);
 const subject = useRef<string | null>(null); subject.current = identity?.user.id ?? null;
 const [assignmentIndex, setAssignmentIndex] = useState(0);
 const [loading, setLoading] = useState(true);
 const [refreshing, setRefreshing] = useState(false);
 const [error, setError] = useState(""); const [notice, setNotice] = useState("");
 const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
 const sequence = useRef(0);
 const appliedSequence = useRef(0);
 const epoch = useRef(0);
 const inFlight = useRef<{ actor: string; epoch: number; promise: Promise<PortalCollections | null> } | null>(null);
 const refresh = useCallback(async (force = false) => {
   const actor = subject.current; if (!actor) return null;
   const currentEpoch = epoch.current;
   if (!force && inFlight.current?.actor === actor && inFlight.current.epoch === currentEpoch) return inFlight.current.promise;
   const request = ++sequence.current; setRefreshing(true);
   const promise = (async () => {
   try {
     const snapshot = await get<PortalCollections>("/portal/snapshot");
     if (subject.current !== actor || epoch.current !== currentEpoch) return null;
     if (request < appliedSequence.current) return currentData.current;
     appliedSequence.current = request;
     if(!isDemoMode) setPortalNow(new Date().toISOString()); currentData.current = snapshot; setAllData(snapshot); setError(""); setRefreshedAt(new Date().toISOString()); return snapshot;
   } catch (cause) {
     if (subject.current === actor && epoch.current === currentEpoch && request >= appliedSequence.current) setError(cause instanceof Error ? cause.message : "Unable to fetch database records.");
     throw cause;
   } finally { if (subject.current === actor && epoch.current === currentEpoch) setLoading(false); if (request === sequence.current) setRefreshing(false); }
   })();
   inFlight.current = { actor, epoch: currentEpoch, promise };
   try { return await promise; } finally { if (inFlight.current?.promise === promise) inFlight.current = null; }
 }, [get]);
 useEffect(() => {
   epoch.current++; inFlight.current = null;
   sequence.current++; appliedSequence.current = 0; currentData.current = null; setAllData(null); setAssignmentIndex(0); setError(""); setRefreshedAt(null);
   if (!identity || !isWorkspace) { setLoading(live.loading); setRefreshing(false); return; }
   setLoading(true); void refresh().catch(() => {});
   if(isDemoMode){
     let dispose:(()=>void)|undefined;let active=true;
     void import("@/lib/demo/repository").then(({demoRepository})=>{if(active) dispose=demoRepository.subscribe(()=>{void refresh().catch(()=>{});});});
     return ()=>{active=false;dispose?.();};
   }
   const timer = window.setInterval(() => { if (document.visibilityState === "visible") void refresh().catch(() => {}); }, 30_000);
   const focus = () => { void refresh().catch(() => {}); }; window.addEventListener("focus", focus);
   return () => { clearInterval(timer); window.removeEventListener("focus", focus); };
 }, [identity, live.loading, refresh, isWorkspace]);
 const user = allData?.users.find(u => u.id === identity?.user.id && u.status === "ACTIVE") ?? null;
 const index = allData && user ? workspaceAssignmentIndex(allData, user, assignmentIndex) : 0;
 const data = useMemo(() => allData && user?.assignments[index] ? scopedSnapshot(allData, user, index) : null, [allData, user, index]);
 const execute = async (command: Command): Promise<CommandResult> => {
   const before = currentData.current; const actor = subject.current;
   if (!before || !actor) throw new Error("Choose a workspace first.");
   const result = isDemoMode
     ? await (await import("@/lib/demo/repository")).demoRepository.execute(command,actor,index)
     : await executeLiveCommand(command, before, live);
   if (subject.current !== actor) throw new Error("Your identity changed. Reopen the workspace to inspect the saved result.");
   let saved: PortalCollections | null = null;
   try { saved = await refresh(true); }
   catch {
     // The mutation already committed. A failed read must not invite another
     // create/approve request or describe the write itself as rejected.
     const message = "Your changes were saved to the database, but the updated view could not load. Use Try again to reload; do not submit the action again.";
     setError(message); setNotice(message);
     return {...result, message, data:currentData.current ?? before};
   }
   const current = saved ?? currentData.current; if (!current) throw new Error("The action was saved; refresh to see its result.");
   setNotice(result.message); return { ...result, data: current };
 };
 const markNotification = async (id: string, read: boolean) => {
   try { await execute({kind: "notification.read", id, values: {read}}); }
   catch (cause) { setNotice(cause instanceof Error ? cause.message : "Notification update failed."); }
 };
 return <Context.Provider value={{allData, data, user, assignmentIndex:index, loading:loading || live.loading || Boolean(identity && !allData && !error), error, notice,
   signedOut:!identity, refreshedAt, refreshing, signIn:live.signInDemo, selectScope:setAssignmentIndex,
   signOut:() => {sequence.current++; currentData.current=null; setAllData(null); void live.signOut();},
   reload:() => {void refresh().catch(() => {});}, markNotification, execute, clearNotice:() => setNotice("")}}><Suspense fallback={null}><WorkspaceRoute onChange={setIsWorkspace}/></Suspense>{children}</Context.Provider>;
}
export function useDemo() { const value=useContext(Context); if (!value) throw new Error("DemoProvider is required"); return value; }
