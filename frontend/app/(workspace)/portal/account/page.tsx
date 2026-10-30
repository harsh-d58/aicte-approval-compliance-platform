"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { isDemoMode } from "@/lib/portal/mode";
import { download } from "@/lib/portal/files";
import { useDemo } from "@/app/portal-ui/DemoProvider";
import { Arrow, Badge, Dialog, PageHeading } from "@/app/portal-ui/ui";
import { roleNames, scopeName } from "@/lib/portal/view-models";
import s from "@/app/portal-ui/portal.module.css";
export default function AccountPage() {
  const { user, allData, assignmentIndex, signOut, reload } = useDemo(); const router = useRouter();
  const [resetOpen, setResetOpen] = useState(false);
  const [error,setError]=useState("");
  if (!user || !allData) return null;
  return <><PageHeading eyebrow="YOUR PORTAL PROFILE" title="Make yourself at home." description="Review your identity, active assignment and demonstration session." />
    {error && <p role="alert">{error}</p>}{isDemoMode && <div className={s.panel}><h2>Browser demo data</h2><p>Business records persist in this browser. Export contains records only; uploaded file bytes are not included.</p><button className={s.secondaryButton} onClick={()=>download(new Blob([JSON.stringify({schema:1,data:allData},null,2)],{type:"application/json"}),"setu-demo-records.json")}>Export demo records</button></div>}
    <div className={s.detailGrid}><div className={s.stack}><section className={s.panel}><div className={s.profileHero}><span className={s.avatar}>{user.displayName.split(" ").map(n => n[0]).join("")}</span><div><h2>{user.displayName}</h2><p>{roleNames[user.assignments[assignmentIndex].role]}</p></div></div><div className={s.detailBody}><dl className={s.definitionList}><div><dt>Email address</dt><dd>{user.email}</dd></div><div><dt>Account status</dt><dd><Badge status={user.status} /></dd></div><div><dt>Identity source</dt><dd>Fictional demonstration profile</dd></div><div><dt>Timezone</dt><dd>Asia/Kolkata · Indian Standard Time</dd></div></dl></div></section><section className={s.panel}><div className={s.panelHeader}><h2>Workspace & session</h2></div><div className={s.detailBody}><div className={s.preference}><div><h3>Active role and scope</h3><p>{scopeName(allData, user, assignmentIndex)}</p></div><Link href="/portal/access" className={s.textLink}>Change<Arrow /></Link></div>{isDemoMode && <div className={s.preference}><div><h3>Reset demonstration data</h3><p>Restore sample records and unread notifications. Keep your selected identity and scope.</p></div><button className={s.textLink} onClick={() => setResetOpen(true)}>Reset</button></div>}<div className={s.preference}><div><h3>End this session</h3><p>Clear your demo identity and return to sign-in.</p></div><button className={s.textLink} onClick={() => { signOut(); router.replace("/login"); }}>Sign out<Arrow /></button></div></div></section></div><aside className={s.stack}><div className={s.noticeCard}><h3>Your access follows your assignment.</h3><p>You can only switch between roles and scopes already assigned to this demonstration identity. Choosing a role does not grant unrestricted institutional access.</p></div><div className={s.noticeCard}><h3>About your profile</h3><p>All names, emails and records in this workspace are fictional. Production profile changes will be managed by the approved identity provider.</p></div></aside></div>
    {resetOpen && <Dialog title="Restore the demonstration?" onClose={() => setResetOpen(false)}><p>This restores the original sample records and unread notifications. Your selected fictional profile and a valid baseline assignment remain active. Locally uploaded files and saved analytical views are retained; clear this site’s browser data to remove those.</p><div className={s.dialogActions}><button className={s.secondaryButton} onClick={() => setResetOpen(false)}>Keep current data</button><button className={s.primaryButton} onClick={async () => { try { await (await import("@/lib/demo/repository")).demoRepository.reset(); setResetOpen(false); reload(); } catch(cause) {setError(cause instanceof Error ? cause.message : "Reset failed");setResetOpen(false);} }}>Restore sample data</button></div></Dialog>}
  </>;
}
