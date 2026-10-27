import Link from "next/link";
import { Empty } from "@/app/portal-ui/ui";
import s from "@/app/portal-ui/portal.module.css";
export default function NotFound() { return <section className={s.panel}><Empty title="This page isn’t available.">Return to your overview to pick up where you left off.</Empty><div className={s.detailBody}><Link href="/portal" className={s.primaryButton}>Back to overview</Link></div></section>; }
