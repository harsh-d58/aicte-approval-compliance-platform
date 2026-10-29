"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { apiGet, liveConfig, refreshSession, signInWithPassword, signOutSession, type AuthSession, type LiveIdentity } from "@/lib/live/client";

const storageKey = "aicte.live.session.v1";
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
      session = await refreshSession(session.refresh_token);
      save(session);
    }
    return session.access_token;
  }, [save]);

  const get = useCallback(async <T,>(path: string): Promise<T> => apiGet<T>(path, await token()), [token]);
  const post = useCallback(async <T,>(path: string, body: unknown, extraHeaders?: Record<string, string>): Promise<T> => {
    return (await import("@/lib/live/client")).apiPost<T>(path, body, await token(), extraHeaders);
  }, [token]);
  const patch = useCallback(async <T,>(path: string, body: unknown, extraHeaders?: Record<string, string>): Promise<T> => {
    return (await import("@/lib/live/client")).apiPatch<T>(path, body, await token(), extraHeaders);
  }, [token]);
  const put = useCallback(async <T,>(path: string, body: unknown, extraHeaders?: Record<string, string>): Promise<T> => {
    return (await import("@/lib/live/client")).apiPut<T>(path, body, await token(), extraHeaders);
  }, [token]);
  const del = useCallback(async <T,>(path: string): Promise<T> => {
    return (await import("@/lib/live/client")).apiDelete<T>(path, await token());
  }, [token]);
  const download = useCallback(async (path: string): Promise<{ blob: Blob; filename: string }> => {
    return (await import("@/lib/live/client")).apiDownload(path, await token());
  }, [token]);

  useEffect(() => {
    let active = true;
    async function restore() {
      if (!configured) { setLoading(false); return; }
      try {
        const raw = sessionStorage.getItem(storageKey);
        const stored = raw ? JSON.parse(raw) as AuthSession : null;
        if (!stored?.access_token || !stored?.refresh_token || !stored?.expires_at) return;
        sessionRef.current = stored;
        const profile = await get<LiveIdentity>("/me");
        if (active) setIdentity(profile);
      } catch (cause) {
        save(null);
        if (active) setError(cause instanceof Error ? cause.message : "Unable to restore session.");
      } finally { if (active) setLoading(false); }
    }
    void restore();
    return () => { active = false; };
  }, [configured, get, save]);

  const signIn = async (email: string, password: string) => {
    if (!configured) throw new Error("Live identity is not configured yet.");
    setError("");
    const session = await signInWithPassword(email, password);
    save(session);
    try {
      const profile = await get<LiveIdentity>("/me");
      setIdentity(profile);
    } catch (cause) {
      save(null);
      throw cause;
    }
  };
  const signInDemo = async (personaId: string) => {
    setError("");
    const response = await fetch(`${liveConfig.apiBaseUrl}/prototype/session`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({persona_id: personaId}), cache: "no-store"});
    if (!response.ok) throw new Error("Demo sign-in is unavailable. Start the backend with prototype demos enabled.");
    const session = await response.json() as AuthSession;
    save(session);
    try { setIdentity(await get<LiveIdentity>("/me")); } catch (cause) { save(null); throw cause; }
  };
  const signOut = async () => {
    const accessToken = sessionRef.current?.access_token;
    const isPrototype = sessionRef.current?.refresh_token === "prototype";
    save(null); setIdentity(null); setError("");
    if (accessToken && !isPrototype) await signOutSession(accessToken);
  };

  return <Context.Provider value={{ identity, loading, error, configured, signIn, signInDemo, signOut, get, post, patch, put, del, download }}>{children}</Context.Provider>;
}

export function useLive() {
  const value = useContext(Context);
  if (!value) throw new Error("LiveProvider is required");
  return value;
}
