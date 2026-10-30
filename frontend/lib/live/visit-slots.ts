import type { PortalCollections } from "@/lib/portal/types";

export function confirmableVisitSlots(visit: PortalCollections["visits"][number], slots: PortalCollections["slots"], now = Date.now()) {
  if (["CONFIRMED", "COMPLETED", "CANCELLED"].includes(visit.status)) return [];
  const selected = new Map<string, PortalCollections["slots"][number]>();
  for (const slot of slots) {
    if (slot.visitId !== visit.id || !slot.feasible || !(Date.parse(slot.expiresAt) > now)) continue;
    const key = `${slot.startAt}/${slot.endAt}`;
    const previous = selected.get(key);
    if (!previous || Date.parse(slot.expiresAt) > Date.parse(previous.expiresAt)) selected.set(key, slot);
  }
  return [...selected.values()].sort((a, b) => a.rank - b.rank);
}
