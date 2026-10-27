/** Proposed page destinations. Do not render links until their pages exist. */
export const portalLinks = {
  modules: {
    M1: "/portal/applications",
    M2: "/portal",
    M3: "/portal/evc",
    M4: "/portal/compliance",
    M5: "/portal/renewals",
  },
  innovations: { audit: "/portal/audit/verify", coordination: "/portal/evc" },
  login: "/login",
  reports: "/portal/reports",
} as const;

export const recordLinks = {
  institution: (id: string) => `/portal/institutions/${encodeURIComponent(id)}`,
  application: (id: string) => `/portal/applications/${encodeURIComponent(id)}`,
  document: (id: string) => `/portal/documents/${encodeURIComponent(id)}`,
  visit: (id: string) => `/portal/evc/${encodeURIComponent(id)}`,
  condition: (id: string) => `/portal/compliance/${encodeURIComponent(id)}`,
  report: (code: string) => `/portal/reports/${encodeURIComponent(code)}`,
} as const;
