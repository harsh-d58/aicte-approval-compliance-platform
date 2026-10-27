"use client";
import { useSyncExternalStore } from "react";
const subscribe = (callback: () => void) => {
  window.addEventListener("popstate", callback); window.addEventListener("portal-filters", callback);
  return () => { window.removeEventListener("popstate", callback); window.removeEventListener("portal-filters", callback); };
};
export function useUrlFilters() {
  const search = useSyncExternalStore(subscribe, () => window.location.search, () => "");
  const params = new URLSearchParams(search);
  function update(values: Record<string, string | null>) {
    const next = new URLSearchParams(window.location.search);
    Object.entries(values).forEach(([key, value]) => { if (value) next.set(key, value); else next.delete(key); });
    window.history.replaceState(null, "", window.location.pathname + (next.size ? `?${next}` : ""));
    window.dispatchEvent(new Event("portal-filters"));
  }
  return { params, update };
}
