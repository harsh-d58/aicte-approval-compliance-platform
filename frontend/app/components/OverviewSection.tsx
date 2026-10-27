"use client";
import Image from "next/image";
import { useState, useSyncExternalStore } from "react";
import demo from "../../public/GIF_1.gif";
import styles from "./OverviewSection.module.css";

export default function OverviewSection() {
  const reduced = useSyncExternalStore(callback => { const media = window.matchMedia("(prefers-reduced-motion: reduce)"); media.addEventListener("change", callback); return () => media.removeEventListener("change", callback); }, () => window.matchMedia("(prefers-reduced-motion: reduce)").matches, () => true);
  const [paused, setPaused] = useState<boolean | null>(null);
  const stopped = paused ?? reduced;
  return (
    <section id="overview" className={`section ${styles.overview}`} aria-labelledby="overview-title">
      <div className={`container ${styles.inner}`}>
        <div className={styles.preview}>
          <div className={styles.previewHeader}><span className={styles.dot} />Platform at a glance</div>
          <div className={styles.demoFrame}>
            {stopped ? <div style={{ aspectRatio: "1.45", display: "grid", placeContent: "center", background: "linear-gradient(140deg,#eef5fb,#e2e9f8)", color: "#183b61", textAlign: "center", padding: 24 }}><strong>One connected workspace</strong><p>Applications · Expert visits · Compliance</p><small>Animated preview paused</small></div> : <><Image src={demo} alt="Animated overview of the platform" unoptimized className={styles.demo} sizes="(max-width: 900px) 100vw, 50vw" /><span className={styles.logoBlur} aria-hidden="true" /></>}
          </div>
          <button type="button" className={styles.link} style={{ padding: "12px 18px", border: 0, background: "transparent", cursor: "pointer" }} onClick={() => setPaused(!stopped)} aria-pressed={stopped}>{stopped ? "Play animated preview" : "Pause animated preview"}</button>
        </div>
        <div className={styles.content}>
          <span className={styles.eyebrow}>One platform. Every stage.</span>
          <h2 id="overview-title">A clearer path from application to approval.</h2>
          <p>Manage applications, review documents and coordinate expert visits through a single, structured workflow.</p>
          <ul>
            <li><strong>Apply with confidence</strong><span>Keep institutional information and documents organised.</span></li>
            <li><strong>Stay informed</strong><span>Follow review stages, observations and compliance actions.</span></li>
            <li><strong>Coordinate seamlessly</strong><span>Connect institutions, officers and expert committees.</span></li>
          </ul>
          <a className={styles.link} href="#workflow">Understand the approval process <span aria-hidden="true">&rarr;</span></a>
        </div>
      </div>
    </section>
  );
}
