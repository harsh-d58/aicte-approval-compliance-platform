export const liveConfig = {
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, "") ?? "",
  supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api/v1",
};

export type LiveAssignment = {
  id: string;
  role_code: string;
  scope_type: string;
  scope_id: string | null;
  valid_from: string | null;
  valid_until: string | null;
};

export type LiveIdentity = {
  user: { id: string; display_name: string; email: string; status: string; last_login_at: string | null };
  assignments: LiveAssignment[];
};

export type LiveRecord = Record<string, string | number | boolean | null> & { id: string };
export type LivePage<T> = { data: T[]; page: { limit: number; next_cursor: string | null } };

export type AuthSession = { access_token: string; refresh_token: string; expires_at: number };

/** Keep identity and workspace reads recoverable when a service stops responding. */
async function boundedRequest<T>(url: string, init: RequestInit, read: (response: Response) => Promise<T>, timeoutMs: number, timeoutMessage: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try { return await read(await fetch(url, { ...init, signal: controller.signal })); }
  catch (cause) {
    if (controller.signal.aborted) throw new Error(timeoutMessage);
    throw cause;
  } finally { clearTimeout(timer); }
}

async function authRequest(path: string, body: object, token?: string): Promise<AuthSession> {
  return boundedRequest(`${liveConfig.supabaseUrl}/auth/v1/${path}`, {
    method: "POST",
    headers: {
      apikey: liveConfig.supabaseKey,
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  }, async response => {
  if (!response.ok) throw new Error(response.status === 400 ? "Sign-in details were not accepted." : "Identity service is unavailable. Please try again.");
  const result = await response.json() as { access_token?: string; refresh_token?: string; expires_in?: number };
  if (!result.access_token || !result.refresh_token || !result.expires_in) throw new Error("Identity service returned an incomplete session.");
  return { access_token: result.access_token, refresh_token: result.refresh_token, expires_at: Date.now() + result.expires_in * 1000 };
  }, 20_000, "Supabase sign-in timed out. Please try again.");
}

export function signInWithPersona(personaId: string): Promise<AuthSession> {
  return boundedRequest(`${liveConfig.apiBaseUrl}/prototype/session`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ persona_id: personaId }), cache: "no-store",
  }, async response => {
    if (!response.ok) throw new Error(await parseError(response, "Demo sign-in is unavailable. Please try again."));
    const session = await response.json() as AuthSession;
    if (!session.access_token || session.refresh_token !== "prototype" || !Number.isFinite(session.expires_at)) throw new Error("Demo sign-in returned an incomplete session. Please try again.");
    return session;
  }, 20_000, "Demo sign-in timed out. The live service is taking too long; please try again.");
}

export function signInWithPassword(email: string, password: string) {
  return authRequest("token?grant_type=password", { email, password });
}

export function refreshSession(refreshToken: string) {
  return authRequest("token?grant_type=refresh_token", { refresh_token: refreshToken });
}

/** Validate a real Supabase session without depending on the Python API. */
export function getSupabaseUser(accessToken: string): Promise<{id:string;email?:string}> {
  return boundedRequest(`${liveConfig.supabaseUrl}/auth/v1/user`, {
    headers:{apikey:liveConfig.supabaseKey,Authorization:`Bearer ${accessToken}`},cache:"no-store",
  },async response=>{
    if(!response.ok) throw new Error("Your Supabase session expired. Sign in again.");
    const user=await response.json() as {id:string;email?:string};
    if(!user.id) throw new Error("Supabase returned an incomplete user profile.");
    return user;
  },20_000,"Supabase profile validation timed out. Please sign in again.");
}

export async function signOutSession(accessToken: string) {
  try {
    await fetch(`${liveConfig.supabaseUrl}/auth/v1/logout`, {
      method: "POST",
      headers: { apikey: liveConfig.supabaseKey, Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
  } catch { /* Local credentials are cleared even if the provider is unreachable. */ }
}

async function parseError(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json() as { detail?: string | unknown; error?: { message?: string; code?: string } };
    if (data.error?.message) return data.error.message;
    if (data?.detail) {
      return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    }
  } catch {
    // Non-JSON body
  }
  if (response.status === 401) return "Your session expired. Sign in again.";
  if (response.status === 403) return "Your account has no authorised access to this workspace.";
  if (response.status === 404) return "This record is unavailable or outside your scope.";
  return fallback;
}

export async function apiGet<T>(path: string, accessToken: string): Promise<T> {
  return boundedRequest(`${liveConfig.apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  }, async response => {
  if (!response.ok) {
    throw new Error(await parseError(response, "The live service could not complete this request. Please try again."));
  }
  return response.json() as Promise<T>;
  }, path === "/me" ? 20_000 : 45_000, path === "/me" ? "Your account could not load in time. Sign in again." : "The workspace took too long to load. Use Try again to reload the live records.");
}

export async function apiPost<T>(path: string, body: unknown, accessToken: string, extraHeaders?: Record<string, string>): Promise<T> {
  const response = await fetch(`${liveConfig.apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...(extraHeaders ?? {}),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Operation rejected by server."));
  }
  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown, accessToken: string, extraHeaders?: Record<string, string>): Promise<T> {
  const response = await fetch(`${liveConfig.apiBaseUrl}${path}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...(extraHeaders ?? {}),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Update rejected by server."));
  }
  return response.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown, accessToken: string, extraHeaders?: Record<string, string>): Promise<T> {
  const response = await fetch(`${liveConfig.apiBaseUrl}${path}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...(extraHeaders ?? {}),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Put operation rejected by server."));
  }
  return response.json() as Promise<T>;
}

export async function apiDelete<T>(path: string, accessToken: string): Promise<T> {
  const response = await fetch(`${liveConfig.apiBaseUrl}${path}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Delete rejected by server."));
  }
  return response.json() as Promise<T>;
}

export async function apiDownload(path: string, accessToken: string): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${liveConfig.apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response, "Download could not be completed."));
  }
  const disposition = response.headers.get("content-disposition");
  let filename = "download";
  if (disposition && disposition.includes("filename=")) {
    filename = disposition.split("filename=")[1].replace(/["']/g, "").trim();
  }
  const blob = await response.blob();
  return { blob, filename };
}
