import type { PortalCollections, Role } from "./types";
import { activeApplication, isOverdue } from "./view-models";

type MetricIcon = "settings" | "alert" | "clock" | "shield" | "document" | "check" | "monitor" | "calendar";
export type DashboardMetric = { title: string; value: number; detail: string; icon: MetricIcon; tone?: string; href?: string };

export function dashboardMetrics(data: PortalCollections, role: Role): DashboardMetric[] {
  if (role === "SYSTEM") return [
    { title: "Async jobs", value: data.jobs.length, detail: "Across demo queues", icon: "settings" },
    { title: "Failed jobs", value: data.jobs.filter(j => j.status === "FAILED").length, detail: "Needs operator attention", icon: "alert", tone: "red" },
    { title: "Queued & retrying", value: data.jobs.filter(j => ["QUEUED", "RETRY_PENDING"].includes(j.status)).length, detail: "Waiting for processing", icon: "clock", tone: "blue" },
    { title: "Connector issues", value: data.integrations.filter(i => ["STALE", "FAILED"].includes(i.status)).length, detail: "Stale or unavailable", icon: "shield", tone: "amber" },
  ];
  if (role === "POLICY") return [
    { title: "Workflow versions", value: data.workflows.length, detail: "Sample configurations", icon: "document" },
    { title: "Published routes", value: data.workflows.filter(w => w.status === "PUBLISHED").length, detail: "Existing cases stay pinned", icon: "check", tone: "green" },
    { title: "Draft versions", value: data.workflows.filter(w => w.status === "DRAFT").length, detail: "Awaiting validation", icon: "clock", tone: "amber" },
    { title: "Rule configurations", value: data.configurations.length, detail: "Illustrative policy values", icon: "settings", tone: "blue" },
  ];
  if (role === "AUDITOR") return [
    { title: "Visible audit events", value: data.auditEvents.length, detail: "Read-only history", icon: "document" },
    { title: "Closed cases", value: data.applications.filter(a => a.closure).length, detail: "Retained final outcomes", icon: "check", tone: "green", href: "/portal/applications?status=closed" },
    { title: "Report categories", value: data.reportDefinitions.length, detail: "Permitted report definitions", icon: "monitor", tone: "blue" },
    { title: "Pending anchors", value: data.auditEvents.filter(a => a.anchor === "PENDING").length, detail: "Optional illustrative ledger", icon: "shield", tone: "amber" },
  ];
  if (role === "EVC_EXPERT" || role === "EVC_COORDINATOR") return [
    { title: "Assigned visits", value: data.visits.length, detail: "Within your active scope", icon: "calendar" },
    { title: "Awaiting confirmation", value: data.visits.filter(v => v.status === "PROPOSED").length, detail: "Proposed, not yet reserved", icon: "clock", tone: "amber" },
    { title: "Records in review", value: data.meetingRecords.filter(r => r.versions.find(v => v.number === r.currentVersion)?.status === "IN_REVIEW").length, detail: "Human approval required", icon: "document", tone: "blue" },
    { title: "Completed visits", value: data.visits.filter(v => v.status === "COMPLETED").length, detail: "Report status tracked separately", icon: "check", tone: "green" },
  ];
  if (role === "COMPLIANCE") {
    const open = data.conditions.filter(c => c.status !== "CLOSED");
    return [
      { title: "Open conditions", value: open.length, detail: "Awaiting verified closure", icon: "shield" },
      { title: "Overdue conditions", value: open.filter(c => isOverdue(c.dueAt)).length, detail: "Needs your attention", icon: "alert", tone: "red" },
      { title: "Renewals in review", value: data.renewals.filter(r => r.status === "UNDER_REVIEW").length, detail: "Evidence awaiting verification", icon: "document", tone: "blue" },
      { title: "Closed conditions", value: data.conditions.filter(c => c.status === "CLOSED").length, detail: "Verified by a reviewer", icon: "check", tone: "green" },
    ];
  }
  return [
    { title: "Active applications", value: data.applications.filter(a => activeApplication(a.status)).length, detail: "Across current review stages", icon: "document", href: "/portal/applications?status=active" },
    { title: role === "INSTITUTION" ? "Action required" : "Assigned tasks", value: data.tasks.filter(t => t.status !== "COMPLETED").length, detail: "Assigned actions in your scope", icon: "alert", tone: "red", href: "/portal/tasks" },
    { title: "Upcoming EVC visits", value: data.visits.filter(v => !["COMPLETED", "CANCELLED"].includes(v.status)).length, detail: "Scheduling in progress", icon: "calendar", tone: "blue" },
    { title: "Renewals in progress", value: data.renewals.filter(r => r.status !== "VERIFIED").length, detail: "Tracked separately from expiry", icon: "shield", tone: "green" },
  ];
}
