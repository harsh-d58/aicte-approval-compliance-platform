"use client";
import s from "@/app/portal-ui/portal.module.css";
export default function ErrorPage({ reset }: { reset: () => void }) { return <div className={s.loadError} role="alert"><h1>Let’s try that again.</h1><p>This workspace could not be displayed. Your demonstration data is still available.</p><button className={s.primaryButton} onClick={reset}>Reload workspace</button></div>; }
