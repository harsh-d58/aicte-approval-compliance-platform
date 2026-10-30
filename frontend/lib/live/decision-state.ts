import type { Application, PortalCollections } from "@/lib/portal/types";

export function decisionState(data: PortalCollections, application: Application) {
  const conditions = data.conditions.filter(row => row.applicationId === application.id);
  const terminal = ["CLOSED", "REJECTED", "WITHDRAWN"].includes(application.status);
  const stage = application.stageType || application.currentStage.toLowerCase();
  let blocker = "";
  if (terminal) blocker = "This application already has a final decision.";
  else if (application.status === "APPROVED") {
    if (conditions.some(condition => condition.status !== "CLOSED")) blocker = "Close every verified approval condition before closing the application.";
  } else if (stage !== "decision" && application.status !== "DECISION_PENDING") blocker = "Complete the configured review route before recording a decision.";
  else if (data.deficiencies.some(notice => notice.applicationId === application.id && notice.items.some(item => item.status !== "RESOLVED"))) blocker = "Resolve every deficiency item before recording a decision.";
  else {
    const workflow = data.workflows.find(row => row.id === application.workflowId);
    const needsVisit = workflow?.stages.some(row => row.type === "evc" || row.code.toUpperCase() === "EVC");
    const hasReport = data.visits.some(visit => visit.applicationId === application.id && visit.status === "COMPLETED"
      && data.meetingRecords.some(record => record.visitId === visit.id && record.type === "EVC_REPORT"
        && record.versions.some(version => version.number === record.currentVersion && version.status === "APPROVED")));
    if (needsVisit && !hasReport) blocker = "Complete the EVC visit and approve its report before recording a decision.";
  }
  return { conditions, blocker, outcomes: blocker ? [] : application.status === "APPROVED" ? ["CLOSE"] : ["APPROVE", "REJECT"],
    canAddCondition: !terminal && (application.status === "APPROVED" || stage === "decision" || application.status === "DECISION_PENDING") };
}
