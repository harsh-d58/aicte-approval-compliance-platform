with open("frontend/lib/portal/view-models.ts", "r", encoding="utf-8") as f:
    text = f.read()

target = """  const expertVisit = scope.type === "EVC" ? data.visits.find(v => v.id === scope.id && v.committee.some(m => data.experts.some(e => e.id === m.expertId && e.userId === user.id))) : undefined;
  const applications = data.applications.filter(a => {
    const institution = data.institutions.find(i => i.id === a.institutionId);
    const within = scope.type === "GLOBAL" || (scope.type === "REGION" && institution?.regionId === scope.id)
      || (scope.type === "INSTITUTION" && a.institutionId === scope.id) || (scope.type === "APPLICATION" && a.id === scope.id)
      || (scope.type === "EVC" && expertVisit?.applicationId === a.id);
    return within && (role !== "SCRUTINY" || a.ownerId === user.id);
  });
  const appIds = new Set(applications.map(a => a.id));
  const institutions = data.institutions.filter(i => scope.type === "GLOBAL" || (scope.type === "REGION" && role !== "SCRUTINY" && i.regionId === scope.id) || applications.some(a => a.institutionId === i.id) || (scope.type === "INSTITUTION" && i.id === scope.id));
  const institutionIds = new Set(institutions.map(i => i.id));
  const visits = data.visits.filter(v => appIds.has(v.applicationId) && (role !== "EVC_EXPERT" || ((scope.type === "EVC" ? v.id === scope.id : appIds.has(v.applicationId)) && v.committee.some(m => data.experts.some(e => e.id === m.expertId && e.userId === user.id)))));"""

replacement = """  const expertVisit = scope.type === "EVC" ? data.visits.find(v => v.id === scope.id && v.committee.some(m => data.experts.some(e => e.id === m.expertId && e.userId === user.id))) : undefined;
  const expertVisits = role === "EVC_EXPERT" ? data.visits.filter(v => v.committee.some(m => data.experts.some(e => e.id === m.expertId && e.userId === user.id))) : [];
  const applications = data.applications.filter(a => {
    const institution = data.institutions.find(i => i.id === a.institutionId);
    const within = scope.type === "GLOBAL" || (scope.type === "REGION" && institution?.regionId === scope.id)
      || (scope.type === "INSTITUTION" && a.institutionId === scope.id) || (scope.type === "APPLICATION" && a.id === scope.id)
      || (scope.type === "EVC" && expertVisit?.applicationId === a.id)
      || (role === "EVC_EXPERT" && expertVisits.some(v => v.applicationId === a.id));
    return within && (role !== "SCRUTINY" || a.ownerId === user.id);
  });
  const appIds = new Set(applications.map(a => a.id));
  const institutions = data.institutions.filter(i => scope.type === "GLOBAL" || (scope.type === "REGION" && role !== "SCRUTINY" && i.regionId === scope.id) || applications.some(a => a.institutionId === i.id) || (scope.type === "INSTITUTION" && i.id === scope.id));
  const institutionIds = new Set(institutions.map(i => i.id));
  const visits = role === "EVC_EXPERT" ? expertVisits : data.visits.filter(v => appIds.has(v.applicationId) && (role !== "EVC_EXPERT" || ((scope.type === "EVC" ? v.id === scope.id : appIds.has(v.applicationId)) && v.committee.some(m => data.experts.some(e => e.id === m.expertId && e.userId === user.id)))));"""

text_norm = text.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
replacement_norm = replacement.replace("\r\n", "\n")

assert target_norm in text_norm, "Target not found"
text_norm = text_norm.replace(target_norm, replacement_norm, 1)

with open("frontend/lib/portal/view-models.ts", "w", encoding="utf-8") as f:
    f.write(text_norm)

print("Successfully replaced!")

