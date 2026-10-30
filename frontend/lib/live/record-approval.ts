import type { PortalCollections } from "@/lib/portal/types";

export function recordApprovalBlock(record: PortalCollections["meetingRecords"][number], visits: PortalCollections["visits"]) {
  if (record.type !== "EVC_REPORT") return "";
  const visit = visits.find(visit => visit.id === record.visitId);
  return visit?.status === "COMPLETED" ? "" : "Complete the EVC visit before approving its report. A confirmed schedule alone is not a completed inspection.";
}
