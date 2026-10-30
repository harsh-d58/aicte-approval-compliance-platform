"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { apiGet, getSupabaseUser, liveConfig, refreshSession, signInWithPassword, signInWithPersona, signOutSession, type AuthSession, type LiveIdentity } from "@/lib/live/client";
import { isDemoMode } from "@/lib/portal/mode";

async function demoIdentity(personaId: string): Promise<LiveIdentity> {
  const {demoRepository}=await import("@/lib/demo/repository");
  const data=await demoRepository.snapshot();
  const user=data.users.find(row=>row.id===personaId && row.status==="ACTIVE");
  if(!user) throw new Error("Choose an active demonstration persona.");
  return {user:{id:user.id,display_name:user.displayName,email:user.email,status:"active",last_login_at:null},
    assignments:user.assignments.map((a,index)=>({id:`${user.id}-${index}`,role_code:a.role,scope_type:a.scope.type.toLowerCase(),scope_id:a.scope.id,valid_from:null,valid_until:a.validUntil}))};
}

async function demoRead<T>(path:string):Promise<T> {
  const {demoRepository}=await import("@/lib/demo/repository");
  if(path.split("?")[0]==="/portal/snapshot") return await demoRepository.snapshot() as T;
  if(path.split("?")[0]==="/audit/verify-chain") return await demoRepository.verifyAudit(new URLSearchParams(path.split("?")[1]).get("simulate")==="true") as T;
  throw new Error("This operation is unavailable in the local demo. Use its demo workspace controls.");
}

const storageKey = isDemoMode ? "aicte.demo.session.v1" : "aicte.live.session.v1";
type LiveContext = {
  identity: LiveIdentity | null;
  loading: boolean;
  error: string;
  configured: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signInDemo: (personaId: string) => Promise<void>;
  get: <T>(path: string) => Promise<T>;
  post: <T>(path: string, body: unknown, extraHeaders?: Record<string, string>) => Promise<T>;
  patch: <T>(path: string, body: unknown, extraHeaders?: Record<string, string>) => Promise<T>;
  put: <T>(path: string, body: unknown, extraHeaders?: Record<string, string>) => Promise<T>;
  del: <T>(path: string) => Promise<T>;
  download: (path: string) => Promise<{ blob: Blob; filename: string }>;
};
const Context = createContext<LiveContext | null>(null);

export function LiveProvider({ children }: { children: React.ReactNode }) {
  const configured = Boolean(liveConfig.supabaseUrl && liveConfig.supabaseKey);
  const sessionRef = useRef<AuthSession | null>(null);
  const generation = useRef(0);
  const refreshing = useRef<{ session: AuthSession; promise: Promise<AuthSession> } | null>(null);
  const [identity, setIdentity] = useState<LiveIdentity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const save = useCallback((value: AuthSession | null) => {
    sessionRef.current = value;
    try {
      if (value) sessionStorage.setItem(storageKey, JSON.stringify(value));
      else sessionStorage.removeItem(storageKey);
    } catch { /* An in-memory session still works until refresh. */ }
  }, []);

  const token = useCallback(async () => {
    let session = sessionRef.current;
    if (!session) throw new Error("Sign in to access the live workspace.");
    if (session.expires_at <= Date.now() + 30_000) {
      if (session.refresh_token === "prototype") throw new Error("Demo session expired. Choose your persona again.");
      const previous = session;
      if (refreshing.current?.session !== previous) refreshing.current = { session: previous, promise: refreshSession(previous.refresh_token) };
      const pending = refreshing.current;
      try {
        session = await pending.promise;
        // A late refresh must never overwrite credentials from a new sign-in.
        if (sessionRef.current !== previous && sessionRef.current !== session) throw new Error("Your session changed. Reopen the workspace.");
        if (sessionRef.current === previous) save(session);
      } finally { if (refreshing.current === pending) refreshing.current = null; }
    }
    return session.access_token;
  }, [save]);

  const get = useCallback(async <T,>(path: string): Promise<T> => isDemoMode ? demoRead<T>(path) : apiGet<T>(path, await token()), [token]);
  const post = useCallback(async <T,>(path: string, body: unknown, extraHeaders?: Record<string, string>): Promise<T> => {
    if(isDemoMode) throw new Error("Use the local demo command adapter for this action.");
    return (await import("@/lib/live/client")).apiPost<T>(path, body, await token(), extraHeaders);
  }, [token]);
  const patch = useCallback(async <T,>(path: string, body: unknown, extraHeaders?: Record<string, string>): Promise<T> => {
    if(isDemoMode) throw new Error("Use the local demo command adapter for this action.");
    return (await import("@/lib/live/client")).apiPatch<T>(path, body, await token(), extraHeaders);
  }, [token]);
  const put = useCallback(async <T,>(path: string, body: unknown, extraHeaders?: Record<string, string>): Promise<T> => {
    if(isDemoMode) throw new Error("Use the local demo command adapter for this action.");
    return (await import("@/lib/live/client")).apiPut<T>(path, body, await token(), extraHeaders);
  }, [token]);
  const del = useCallback(async <T,>(path: string): Promise<T> => {
    if(isDemoMode) throw new Error("Use the local demo command adapter for this action.");
    return (await import("@/lib/live/client")).apiDelete<T>(path, await token());
  }, [token]);
  const download = useCallback(async (path: string): Promise<{ blob: Blob; filename: string }> => {
    if(isDemoMode) throw new Error("Use the locally saved file or report download.");
    return (await import("@/lib/live/client")).apiDownload(path, await token());
  }, [token]);

  useEffect(() => {
    let active = true;
    const attempt = ++generation.current;
    const isCurrent = () => active && attempt === generation.current;
    async function restore() {
      try {
        const raw = sessionStorage.getItem(storageKey);
        const stored = raw ? JSON.parse(raw) as AuthSession : null;
        if (!stored?.access_token || !stored?.refresh_token || !stored?.expires_at) return;
        if (!configured && stored.refresh_token !== "prototype") throw new Error("Supabase sign-in is not configured.");
        sessionRef.current = stored;
        let profile:LiveIdentity;
        if(isDemoMode){
          if(stored.refresh_token!=="prototype") await getSupabaseUser(await token());
          profile=await demoIdentity(stored.refresh_token==="prototype" ? stored.access_token.replace(/^demo:/,"") : "user-institution");
        }else profile = await get<LiveIdentity>("/me");
        if (isCurrent()) { setIdentity(profile); setError(""); }
      } catch (cause) {
        if (isCurrent()) { save(null); setIdentity(null); setError(cause instanceof Error ? cause.message : "Unable to restore session."); }
      } finally { if (isCurrent()) setLoading(false); }
    }
    void restore();
    return () => { active = false; };
  }, [configured, get, save, token]);

  const establish = async (createSession: () => Promise<AuthSession>) => {
    const attempt = ++generation.current;
    setError(""); setLoading(true); setIdentity(null); save(null);
    try {
      const session = await createSession();
      if (attempt !== generation.current) throw new Error("Your sign-in changed. Choose your workspace again.");
      // Validate the profile with this exact token, never a concurrent session.
      let profile:LiveIdentity;
      if(isDemoMode){
        if(session.refresh_token!=="prototype") await getSupabaseUser(session.access_token);
        profile=await demoIdentity(session.refresh_token==="prototype" ? session.access_token.replace(/^demo:/,"") : "user-institution");
      }else profile = await apiGet<LiveIdentity>("/me", session.access_token);
      if (attempt !== generation.current) throw new Error("Your sign-in changed. Choose your workspace again.");
      save(session); setIdentity(profile);
    } catch (cause) {
      if (attempt === generation.current) { save(null); setIdentity(null); }
      throw cause;
    } finally { if (attempt === generation.current) setLoading(false); }
  };
  const signIn = async (email: string, password: string) => {
    if (!configured) throw new Error("Live identity is not configured yet.");
    await establish(() => signInWithPassword(email, password));
  };
  const signInDemo = async (personaId: string) => {
    await establish(() => isDemoMode ? Promise.resolve({access_token:`demo:${personaId}`,refresh_token:"prototype",expires_at:Date.now()+86400000}) : signInWithPersona(personaId));
  };
  const signOut = async () => {
    generation.current++;
    const accessToken = sessionRef.current?.access_token;
    const isPrototype = sessionRef.current?.refresh_token === "prototype";
    save(null); setIdentity(null); setError(""); setLoading(false);
    if (accessToken && !isPrototype) await signOutSession(accessToken);
  };

  return <Context.Provider value={{ identity, loading, error, configured, signIn, signInDemo, signOut, get, post, patch, put, del, download }}>{children}</Context.Provider>;
}

export function useLive() {
  const value = useContext(Context);
  if (!value) throw new Error("LiveProvider is required");
  return value;
}
