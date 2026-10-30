/** Static-export record routes share one built placeholder, with IDs in a query. */
export const recordPatterns = [
  "/portal/applications/[applicationId]/deficiencies/[noticeId]",
  "/portal/documents/[documentId]/checks/[checkId]",
  "/portal/evc/[visitId]/records/new", "/portal/evc/[visitId]/committee",
  "/portal/evc/[visitId]/observations", "/portal/evc/[visitId]/schedule",
  "/portal/applications/[applicationId]/decision", "/portal/applications/[applicationId]/edit",
  "/portal/applications/[applicationId]/review", "/portal/applications/[applicationId]",
  "/portal/reports/[reportCode]", "/portal/report-runs/[runId]", "/portal/renewals/[renewalId]",
  "/portal/notifications/[notificationId]", "/portal/meeting-records/[recordId]",
  "/portal/institutions/[institutionId]", "/portal/evc/[visitId]",
  "/portal/documents/[documentId]", "/portal/compliance/[conditionId]",
  "/portal/admin/workflows/[workflowId]", "/portal/admin/users/[userId]",
];
const staticPaths = new Set(["/portal/applications/new", "/portal/documents/new", "/portal/institutions/new", "/portal/evc/calendar", "/portal/admin/workflows/new"]);

export function routeMatch(pathname: string) {
  const path = pathname.replace(/\/$/, "");
  if (staticPaths.has(path)) return null;
  for (const pattern of recordPatterns) {
    const expected = pattern.split("/"), actual = path.split("/");
    if (expected.length !== actual.length) continue;
    const params: Record<string,string> = {};
    if (!expected.every((segment,i) => segment.startsWith("[") ? Boolean(params[segment.slice(1,-1)] = decodeURIComponent(actual[i] || "")) : segment === actual[i])) continue;
    return {pattern,params,placeholder:expected.map(segment=>segment.startsWith("[")?"item":segment).join("/")};
  }
  return null;
}

export function staticHref(href: string): string {
  if (!href.startsWith("/") || href.startsWith("//")) return href;
  const url = new URL(href,"https://static.invalid");
  if (url.searchParams.has("__path")) return href;
  const matched = routeMatch(url.pathname);
  if (!matched) return href;
  url.searchParams.set("__path",url.pathname);
  return matched.placeholder + "/" + url.search + url.hash;
}
