"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { portalDataSource } from "@/lib/portal/data-source";
import { demoNow, scopedSnapshot } from "@/lib/portal/view-models";
import type { PortalCollections, User } from "@/lib/portal/types";
import { applyCommand, type Command, type CommandResult } from "@/lib/portal/commands";

const sessionKey = "aicte.demo.session.v1";
const dataKey = "aicte.demo.records.v2";
type Session = { userId: string; assignmentIndex: number };
type DemoContext = {
  allData: PortalCollections | null; data: PortalCollections | null; user: User | null;
  assignmentIndex: number; loading: boolean; error: string; notice: string; signedOut: boolean;
  signIn: (id: string) => void; selectScope: (index: number) => void; signOut: () => void;
  reload: () => void; markNotification: (id: string, read: boolean) => void;
  execute: (command: Command) => CommandResult; clearNotice: () => void;
};
const Context = createContext<DemoContext | null>(null);
export function DemoProvider({ children }: { children: React.ReactNode }) {
  const [allData, setAllData] = useState<PortalCollections | null>(null);
  const currentData = useRef<PortalCollections | null>(null);
  const currentSession = useRef<Session | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [signedOut, setSignedOut] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    portalDataSource.getSnapshot().then(seed => {
      if (!active) return;
      let snapshot = seed;
      try { const stored = JSON.parse(sessionStorage.getItem(dataKey) ?? "null"); if (stored && Array.isArray(stored.applications) && Array.isArray(stored.users) && Array.isArray(stored.auditEvents)) snapshot = stored; } catch { /* Use baseline when storage is unavailable. */ }
      let restored: Session | null = null;
      try {
        const raw = JSON.parse(sessionStorage.getItem(sessionKey) ?? "null") as Session | null;
        const account = snapshot.users.find(u => u.id === raw?.userId && u.status === "ACTIVE");
        const assignment = account?.assignments[raw?.assignmentIndex ?? -1];
        if (account && assignment && (!assignment.validUntil || Date.parse(assignment.validUntil) >= Date.parse(demoNow))) restored = raw; else if(account){const first=account.assignments.findIndex(a=>!a.validUntil||Date.parse(a.validUntil)>=Date.parse(demoNow));if(first>=0)restored={userId:account.id,assignmentIndex:first};}
      } catch { /* A blocked or outdated session store falls back to signed out. */ }
      currentData.current = snapshot; currentSession.current = restored; setAllData(snapshot); setSession(restored); setError(""); setLoading(false);
    }).catch(() => { if (active) { setError("We couldn't load the demonstration data. Please try again."); setLoading(false); } });
    return () => { active = false; };
  }, [attempt]);
  const saveSession = useCallback((next: Session | null) => {
    currentSession.current = next;
    setSession(next); setNotice("");
    try { if (next) sessionStorage.setItem(sessionKey, JSON.stringify(next)); else sessionStorage.removeItem(sessionKey); }
    catch { setNotice("Browser storage is unavailable. This demo session will end when you refresh."); }
  }, []);
  const user = allData?.users.find(u => u.id === session?.userId && u.status === "ACTIVE") ?? null;
  const assignmentIndex = session?.assignmentIndex ?? 0;
  const data = useMemo(() => allData && user ? scopedSnapshot(allData, user, assignmentIndex) : null, [allData, user, assignmentIndex]);
  const signIn = (id: string) => {
    const account = allData?.users.find(u => u.id === id && u.status === "ACTIVE");
    const index = account?.assignments.findIndex(a => !a.validUntil || Date.parse(a.validUntil) >= Date.parse(demoNow)) ?? -1;
    if (account && index >= 0) { setSignedOut(false); saveSession({ userId: id, assignmentIndex: index }); }
  };
  const selectScope = (index: number) => {
    const assignment = user?.assignments[index];
    if (user && assignment && (!assignment.validUntil || Date.parse(assignment.validUntil) >= Date.parse(demoNow))) saveSession({ userId: user.id, assignmentIndex: index });
  };
  const signOut = () => { setSignedOut(true); saveSession(null); setAllData(null); currentData.current = null; setLoading(true); setAttempt(a => a + 1); };
  const reload = () => { try { sessionStorage.removeItem(dataKey); } catch {} setNotice(""); setLoading(true); setAttempt(a => a + 1); };
  const execute = (command: Command) => {
    if (!currentData.current || !user) throw new Error("Choose a demonstration identity first.");
    if (currentSession.current?.userId !== user.id || currentSession.current.assignmentIndex !== assignmentIndex) throw new Error("Your active identity or scope changed. Reopen the action in the current workspace.");
    const result = applyCommand(currentData.current, user, assignmentIndex, command);
    currentData.current = result.data; setAllData(result.data); setNotice(result.message);
    try { sessionStorage.setItem(dataKey, JSON.stringify(result.data)); } catch { setNotice(`${result.message} Browser storage is full or unavailable; changes remain in memory.`); }
    return result;
  };
  const markNotification = (id: string, read: boolean) => { execute({ kind: "notification.read", id, values: { read } }); setNotice(""); };
  return <Context.Provider value={{ allData, data, user, assignmentIndex, loading, error, notice, signedOut, signIn, selectScope, signOut, reload, markNotification, execute, clearNotice: () => setNotice("") }}>{children}</Context.Provider>;
}
export function useDemo() { const value = useContext(Context); if (!value) throw new Error("DemoProvider is required"); return value; }
