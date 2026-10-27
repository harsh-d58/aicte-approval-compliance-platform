"use client";
import DeliveryMonitor from "@/app/portal-ui/DeliveryMonitor";
import Link from "next/link";
import Icon from "@/app/components/Icon";
import { useDemo } from "@/app/portal-ui/DemoProvider";
import { Arrow, Badge, Empty, PageHeading, tabKeys } from "@/app/portal-ui/ui";
import { useUrlFilters } from "@/app/portal-ui/useUrlFilters";
import { formatDate, humanize } from "@/lib/portal/view-models";
import s from "@/app/portal-ui/portal.module.css";
const descriptions: Record<string, string> = { DEFICIENCY_ISSUED: "A document clarification has been requested. Review the notice in your application workspace.", CONDITION_OVERDUE: "A compliance condition has passed its sample due date and still needs verified closure.", EVC_INVITATION: "You have been invited to an assigned expert committee visit." };
export default function NotificationsPage() {
  const { data, user, assignmentIndex, markNotification } = useDemo(); const { params, update } = useUrlFilters();
  if (!data) return null;
  if(params.get("view")==="delivery")return <DeliveryMonitor/>;
  const operator=!!user && ["CENTRAL","SYSTEM"].includes(user.assignments[assignmentIndex].role) && user.assignments[assignmentIndex].scope.type==="GLOBAL";
  const unreadOnly = params.get("view") === "unread";
  const notifications = data.notifications.filter(n => !unreadOnly || !n.read);
  return <><PageHeading eyebrow="STAY IN THE LOOP" title="Your notifications." description="Updates and reminders addressed to you, with the context to take your next step." action={<button className={s.secondaryButton} disabled={!data.notifications.some(n => !n.read)} onClick={() => data.notifications.forEach(n => markNotification(n.id, true))}>Mark all as read<Icon name="check" size={15} /></button>} />
    {operator&&<Link className={s.primaryButton} href="/portal/notifications?view=delivery">Open delivery monitoring →</Link>}<section className={s.panel}><div className={s.tabs} role="tablist" onKeyDown={tabKeys} aria-label="Notification views"><button role="tab" tabIndex={!unreadOnly ? 0 : -1} id="all-notifications" aria-selected={!unreadOnly} aria-controls="notification-results" className={s.tab} onClick={() => update({ view: null })}>All notifications<span>{data.notifications.length}</span></button><button role="tab" tabIndex={unreadOnly ? 0 : -1} id="unread-notifications" aria-selected={unreadOnly} aria-controls="notification-results" className={s.tab} onClick={() => update({ view: "unread" })}>Unread<span>{data.notifications.filter(n => !n.read).length}</span></button></div>
    <div id="notification-results" role="tabpanel" aria-labelledby={unreadOnly ? "unread-notifications" : "all-notifications"}>{notifications.length ? notifications.map(n => {
      const appId = n.entityType === "APPLICATION" ? n.entityId : n.entityType === "CONDITION" ? data.conditions.find(c => c.id === n.entityId)?.applicationId : n.entityType === "EVC" ? data.visits.find(v => v.id === n.entityId)?.applicationId : undefined;
      return <article className={`${s.notification} ${!n.read ? s.unread : ""}`} key={n.id}><span className={`${s.priorityIcon} ${n.event.includes("OVERDUE") ? s.red : s.orange}`}><Icon name={n.event.includes("OVERDUE") ? "alert" : "bell"} size={18} /></span><div className={s.notificationContent}><h3>{humanize(n.event)}{!n.read && <span className={s.unreadLabel}>Unread</span>}</h3><p>{descriptions[n.event] ?? "A new update is available for an associated record."}</p><small>{formatDate(n.createdAt)} · {humanize(n.channel)} · IST</small><div className={s.notificationActions}>{appId && <Link href={`/portal/applications/${appId}`} className={s.textLink} onClick={() => markNotification(n.id, true)}>View application<Arrow /></Link>}<button className={s.textLink} onClick={() => markNotification(n.id, !n.read)}>Mark as {n.read ? "unread" : "read"}</button><Link href={`/portal/notifications/${n.id}`} className={s.textLink}>Delivery details<Arrow /></Link><Badge status={n.status} /></div></div></article>;
    }) : <Empty title={unreadOnly ? "You’re up to date." : "A little quiet, for now."} icon="bell">{unreadOnly ? "There are no unread notifications in this workspace." : "Notifications will appear here when an update is addressed to you."}</Empty>}</div><div className={s.tableFoot}>Read status is personal. External delivery status is tracked separately.</div></section>
  </>;
}
