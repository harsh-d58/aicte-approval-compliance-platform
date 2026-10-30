import type { PortalCollections } from "@/lib/portal/types";

type Case = PortalCollections["applications"][number];
type Item = PortalCollections["deficiencies"][number]["items"][number];

export function compatibleEvidence(data: PortalCollections, application: Case, item: Item) {
  const mandated = data.documents.find(document => document.id === item.documentId);
  return data.documents.filter(document => document.institutionId === application.institutionId
    && (!document.applicationId || document.applicationId === application.id)
    && (!mandated || document.type === mandated.type))
    .flatMap(document => document.versions.filter(version => version.verification !== "REJECTED")
      .map(version => ({ document, version })));
}

export function deficiencyResponses(data: PortalCollections, noticeId: string, values: Record<string, unknown>) {
  const notice = data.deficiencies.find(row => row.id === noticeId);
  const application = data.applications.find(row => row.id === notice?.applicationId);
  if (!notice || !application) throw new Error("Deficiency notice unavailable.");
  const explicit = Array.isArray(values.itemResponses) ? values.itemResponses as Array<Record<string, unknown>> : null;
  const selected = values.documentVersionIds ?? values.versionIds;
  const versionIds = Array.isArray(selected) ? selected.map(String) : [];
  return notice.items.filter(item => item.status !== "RESOLVED").map(item => {
    const entry = explicit?.find(response => response.itemId === item.id);
    const compatible = compatibleEvidence(data, application, item);
    const matches = compatible.filter(option => entry ? option.version.id === entry.versionId : versionIds.includes(option.version.id));
    if (matches.length > 1) throw new Error(`Choose one exact evidence version for ${item.criterion || item.description}.`);
    if ((entry?.versionId || versionIds.length || item.documentId) && matches.length !== 1)
      throw new Error(`Select a compatible evidence version for ${item.criterion || item.description}, or upload a new version first.`);
    const narrative = String(entry?.narrative ?? values.response ?? "").trim();
    if (narrative.length < 3) throw new Error("Explain the correction before submitting.");
    return { item_id: item.id, related_document_id: matches[0]?.document.id ?? null,
      document_version_id: matches[0]?.version.id ?? null, narrative };
  });
}
