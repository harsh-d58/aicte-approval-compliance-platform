"use client";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef } from "react";
import Icon, { type IconName } from "@/app/components/Icon";
import { humanize } from "@/lib/portal/view-models";
import s from "./portal.module.css";

export function Brand({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className={s.brand} aria-label="SETU Portal home"><Image src="/setu_logo.png" alt="SETU Logo" width={48} height={48} unoptimized className={s.brandLogo} /><span><strong>SETU Portal</strong><small>{compact ? "Approval & compliance" : "Approval & Compliance Platform"}</small></span></Link>;
}
export function Arrow({ back = false }: { back?: boolean }) { return <span aria-hidden="true">{back ? "←" : "→"}</span>; }
export function tabKeys(event: React.KeyboardEvent<HTMLDivElement>) {
  const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
  if (!keys.includes(event.key)) return;
  const tabs = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
  const index = tabs.findIndex(tab => tab === event.target);
  if (index < 0) return;
  event.preventDefault();
  const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
  tabs[nextIndex].focus(); tabs[nextIndex].click();
}
export function Badge({ status }: { status: string }) {
  const positive = ["CLOSED","APPROVED","VERIFIED","DELIVERED","COMPLETED","ACTIVE","PUBLISHED","COMPLIANT","VERIFIED_COMPLIANT","ACCEPTED","RESOLVED"];
  const negative = ["RETURNED_FOR_DEFICIENCY","OVERDUE","FAILED","REJECTED","BLOCKED","CLARIFICATION_REQUIRED","NON_COMPLIANT","VERIFIED_NON_COMPLIANT","CORRECTION_REQUIRED"];
  const tone = positive.includes(status) ? "green" : negative.includes(status) ? "red" : ["DRAFT","WITHDRAWN","DISABLED","CANCELLED","RETIRED"].includes(status) ? "muted" : "amber";
  return <span className={`${s.badge} ${s[tone]}`}><span aria-hidden="true" />{humanize(status)}</span>;
}
export function Empty({ title = "Nothing here yet", children, icon = "document" }: { title?: string; children?: React.ReactNode; icon?: IconName }) {
  return <div className={s.empty}><span className={s.emptyIcon}><Icon name={icon} size={26} /></span><h3>{title}</h3><p>{children ?? "Your records will appear here when they're available."}</p></div>;
}
export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className={s.pageHeading}><div><span className={s.eyebrow}>{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
export function Metric({ title, value, detail, icon, tone = "orange", href }: { title: string; value: number; detail: string; icon: IconName; tone?: string; href?: string }) {
  const content = <><div className={s.metricTop}><span>{title}</span><span className={`${s.metricIcon} ${s[tone]}`}><Icon name={icon} size={19} /></span></div><strong className={s.metricValue}>{String(value)}</strong><div className={s.metricBottom}><span>{detail}</span>{href && <Arrow />}</div></>;
  return href ? <Link className={s.metric} href={href}>{content}</Link> : <div className={s.metric}>{content}</div>;
}
export function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close(); }, []);
  return <dialog ref={ref} className={s.dialog} onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) { const r = e.currentTarget.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) onClose(); } }} aria-labelledby="dialog-title"><div className={s.dialogHeading}><h2 id="dialog-title">{title}</h2><button onClick={onClose} className={s.iconButton} aria-label="Close dialog">×</button></div>{children}</dialog>;
}
export function Loading() { return <div className={s.loading} role="status"><span className={s.spinner} />Preparing your workspace…</div>; }
