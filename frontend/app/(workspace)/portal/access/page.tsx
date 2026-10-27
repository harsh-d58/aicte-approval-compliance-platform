"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Icon from "@/app/components/Icon";
import { useDemo } from "@/app/portal-ui/DemoProvider";
import { PageHeading, Arrow } from "@/app/portal-ui/ui";
import { demoNow, formatDate, roleNames, safeReturnTo, scopeName } from "@/lib/portal/view-models";
import s from "@/app/portal-ui/portal.module.css";
export default function AccessPage() {
  const { user, allData, assignmentIndex, selectScope } = useDemo(); const router = useRouter();
  const [selected, setSelected] = useState<number | null>(null);
  if (!user || !allData) return null;
  const current = selected ?? assignmentIndex;
  return <><PageHeading eyebrow="YOUR ACCESS" title="Choose your workspace." description="Select the role and scope you want to work in. Only your authorised assignments appear here." />
    <div className={s.scopeCards}>{user.assignments.map((assignment, index) => { const expired = !!assignment.validUntil && Date.parse(assignment.validUntil) < Date.parse(demoNow); return <button className={s.scopeCard} key={`${assignment.role}-${assignment.scope.id}`} aria-pressed={current === index} disabled={expired} onClick={() => setSelected(index)}><Icon name={assignment.scope.type === "INSTITUTION" ? "institution" : assignment.scope.type === "EVC" ? "calendar" : "map"} size={27} /><span className={s.selectionMark} /><strong>{roleNames[assignment.role]}</strong><p>{scopeName(allData, user, index)}</p><small>{expired ? "Assignment expired" : assignment.validUntil ? `Authorised until ${formatDate(assignment.validUntil)}` : "Active assignment · no scheduled expiry"}</small></button>; })}</div>
    <div className={s.scopeFooter}><p><Icon name="shield" size={14} /> Your workspace controls which records you can see.</p><button className={s.primaryButton} onClick={() => { selectScope(current); const destination = safeReturnTo(new URLSearchParams(window.location.search).get("returnTo")); router.push(destination === "/portal/access" ? "/portal" : destination); }}>Continue to workspace<Arrow /></button></div>
  </>;
}
