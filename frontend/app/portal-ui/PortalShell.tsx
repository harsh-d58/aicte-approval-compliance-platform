"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import Icon from "@/app/components/Icon";
import { roleNames, scopeName } from "@/lib/portal/view-models";
import { useDemo } from "./DemoProvider";
import { Brand, Loading } from "./ui";
import PendingPortal from "./PendingPortal";
import s from "./portal.module.css";

const nav = [
  { href: "/portal", label: "Overview", icon: "monitor" as const },
  { href: "/portal/tasks", label: "My tasks", icon: "check" as const },
  { href: "/portal/applications", label: "Applications", icon: "document" as const },
  { href: "/portal/institutions", label: "Institutions", icon: "institution" as const },
  { href: "/portal/documents", label: "Documents", icon: "document" as const },
  { href: "/portal/renewals", label: "Expiry & renewals", icon: "calendar" as const },
  { href: "/portal/evc", label: "Expert visits", icon: "calendar" as const },
  { href: "/portal/availability", label: "Availability", icon: "calendar" as const },
  { href: "/portal/compliance", label: "Compliance", icon: "shield" as const },
  { href: "/portal/reports", label: "Reports", icon: "monitor" as const },
  { href: "/portal/audit", label: "Audit & integrity", icon: "shield" as const },
  { href: "/portal/admin/workflows", label: "Policy & rules", icon: "settings" as const },
  { href: "/portal/admin/users", label: "Administration", icon: "settings" as const },
  { href: "/portal/notifications", label: "Notifications", icon: "bell" as const },
];
const subscribeMobile = (callback: () => void) => { const media = window.matchMedia("(max-width: 800px)"); media.addEventListener("change", callback); return () => media.removeEventListener("change", callback); };
export default function PortalShell({ children }: { children: React.ReactNode }) {
  const { loading, error, user, allData, data, assignmentIndex, signOut, reload, notice, signedOut, refreshedAt, refreshing } = useDemo();
  const pathname = usePathname(); const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);const [collapsed,setCollapsed]=useState(false);
  const mobile = useSyncExternalStore(subscribeMobile, () => window.matchMedia("(max-width: 800px)").matches, () => false);
  const sidebarRef = useRef<HTMLElement>(null);
  const menuRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!mobileOpen || !mobile) return;
    const previousOverflow = document.body.style.overflow;
    const returnFocus = menuRef.current;
    document.body.style.overflow = "hidden";
    sidebarRef.current?.querySelector<HTMLElement>("button, a")?.focus();
    return () => { document.body.style.overflow = previousOverflow; returnFocus?.focus(); };
  }, [mobileOpen, mobile]);
  useEffect(() => {
    if (!loading && !error && !user) router.replace(signedOut ? "/login" : `/login?returnTo=${encodeURIComponent(pathname + window.location.search)}`);
  }, [loading, error, user, pathname, router, signedOut]);
  if (loading) return <PendingPortal fallback={<Loading />}>{children}</PendingPortal>;
  if (error) return <PendingPortal fallback={<div className={s.loadError} role="alert"><h1>Unable to open your workspace</h1><p>{error}</p><button className={s.primaryButton} onClick={reload}>Try again</button></div>}>{children}</PendingPortal>;
  if (!user || !allData || !data) return <PendingPortal fallback={<Loading />}>{children}</PendingPortal>;
  const assignment = user.assignments[assignmentIndex];
  const unread = data.notifications.filter(n => !n.read).length;
  const label = pathname === "/portal" ? "Overview" : pathname.includes("/applications/") ? "Application workspace" : [...nav, { href: "/portal/account", label: "My account" }, { href: "/portal/access", label: "Role & scope" }].find(n => n.href === pathname)?.label ?? "Workspace";
  return <div className={`${s.workspace} ${collapsed?s.workspaceCollapsed:""}`}>
    {mobileOpen && <button className={s.scrim} onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
    <aside id="portal-navigation" ref={sidebarRef} inert={mobile && !mobileOpen} role={mobile && mobileOpen ? "dialog" : undefined} aria-modal={mobile && mobileOpen ? true : undefined} onKeyDown={e => {
      if (!mobile || !mobileOpen) return;
      if (e.key === "Escape") { e.preventDefault(); setMobileOpen(false); }
      if (e.key === "Tab") { const nodes = sidebarRef.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])'); if (!nodes?.length) return; const first = nodes[0]; const last = nodes[nodes.length - 1]; if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); } }
    }} className={`${s.sidebar} ${mobileOpen ? s.sidebarOpen : ""}`} aria-label="Portal navigation">
      <div className={s.sidebarBrand}><Brand compact /><button className={s.mobileClose} onClick={() => setMobileOpen(false)} aria-label="Close navigation">×</button></div>
      <Link className={s.contextCard} href="/portal/access" onClick={() => setMobileOpen(false)}><span className={s.contextIcon}><Icon name="institution" size={20} /></span><span><small>YOUR WORKSPACE</small><strong>{assignment.scope.type === "INSTITUTION" ? "Institution workspace" : assignment.scope.type === "EVC" ? "Committee workspace" : assignment.scope.type === "REGION" ? "Regional workspace" : "Central workspace"}</strong><span>{roleNames[assignment.role]}</span><small>{scopeName(allData, user, assignmentIndex)}</small></span><span aria-hidden="true">⌄</span></Link>
      <div className={s.navLabel}><span>WORKSPACE</span><button className={s.collapseButton} onClick={()=>setCollapsed(v=>!v)} aria-expanded={!collapsed} aria-controls="portal-navigation" aria-label={collapsed?"Expand navigation":"Collapse navigation"}>{collapsed?"→":"←"}</button></div>
      <nav className={s.sideNav}>{nav.filter(n => n.href === "/portal/admin/workflows" ? ["POLICY", "CENTRAL"].includes(assignment.role) : n.href === "/portal/admin/users" ? assignment.role === "SYSTEM" : n.href === "/portal/availability" ? ["INSTITUTION", "EVC_EXPERT"].includes(assignment.role) : ["/portal/applications", "/portal/institutions", "/portal/documents", "/portal/renewals", "/portal/evc", "/portal/compliance"].includes(n.href) ? !["POLICY", "SYSTEM"].includes(assignment.role) : true).map(n => <Link key={n.href} aria-label={n.label} title={n.label} href={n.href} onClick={() => setMobileOpen(false)} aria-current={(n.href === "/portal" ? pathname === n.href : pathname.startsWith(n.href)) ? "page" : undefined} className={s.sideLink}><Icon name={n.icon} size={20} /><span>{n.label}</span>{n.href.endsWith("tasks") && data.tasks.length > 0 && <span className={s.count}>{data.tasks.length}</span>}{n.href.endsWith("notifications") && unread > 0 && <span className={s.count}>{unread}</span>}</Link>)}</nav>
      <div className={s.sidebarBottom}><div className={s.demoNote}><span className={s.liveDot} />Live Cloud Workspace<p>Authoritative records from Supabase PostgreSQL. Changes are committed live to the database.</p></div><Link href="/portal/account" onClick={() => setMobileOpen(false)} className={`${s.sideLink} ${s.accountLink}`} aria-current={pathname === "/portal/account" ? "page" : undefined}><span className={s.avatar}>{user.displayName.split(" ").map(n => n[0]).join("")}</span><span><strong>{user.displayName}</strong><small>My account & session</small></span><ArrowRight /></Link></div>
    </aside>
    <div className={s.mainColumn} inert={mobile && mobileOpen}><header className={s.topbar}><div className={s.breadcrumb}><button ref={menuRef} className={`${s.iconButton} ${s.menuButton}`} onClick={() => setMobileOpen(true)} aria-label="Open navigation" aria-expanded={mobileOpen}><Icon name="menu" size={22} /></button><Link href="/portal">Workspace</Link><span>/</span><strong>{label}</strong></div><div className={s.topActions}><button className={s.demoChip} onClick={reload} disabled={refreshing} title={refreshedAt ? `Last fetched ${new Date(refreshedAt).toLocaleTimeString("en-IN", {timeZone:"Asia/Kolkata"})} IST` : "Fetch database records"}>{refreshing ? "Refreshing…" : "Live data · Refresh"}</button><Link href="/portal/notifications" className={s.iconButton} aria-label={`Notifications, ${unread} unread`}><Icon name="bell" size={20} />{unread > 0 && <span className={s.notificationDot} />}</Link><span className={s.topDivider} /><button className={s.signOut} aria-label="Sign out" onClick={() => { signOut(); router.replace("/login"); }}><Icon name="logout" size={17} /><span>Sign out</span></button></div></header>
      <main id="main-content" className={s.content}>{notice && <p className={s.inlineNotice} role="status">{notice}</p>}{children}</main>
      <footer className={s.workspaceFooter}><span>AICTE Approval & Compliance Platform</span><span title={scopeName(allData, user, assignmentIndex)}>Production · Supabase PostgreSQL · IST</span></footer>
    </div>
  </div>;
}
function ArrowRight() { return <span aria-hidden="true">→</span>; }

