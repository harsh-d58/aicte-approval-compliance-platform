import type { PortalCollections, User } from "@/lib/portal/types";

/** Prefer an expert's actual selected committee over an unused legacy scope. */
export function workspaceAssignmentIndex(data: PortalCollections, user: User, requested: number) {
  const index = user.assignments[requested] ? requested : 0;
  const current = user.assignments[index];
  if (!current || current.role !== "EVC_EXPERT") return index;
  const assigned = data.visits.filter(visit => visit.committee.some(member =>
    data.experts.some(expert => expert.id === member.expertId && expert.userId === user.id)));
  const matches = (assignment: User["assignments"][number]) => assignment.role === "EVC_EXPERT" && assigned.some(visit =>
    assignment.scope.type === "EVC" ? assignment.scope.id === visit.id
      : assignment.scope.type === "APPLICATION" ? assignment.scope.id === visit.applicationId : false);
  if (matches(current)) return index;
  const alternative = user.assignments.findIndex(matches);
  return alternative >= 0 ? alternative : index;
}
