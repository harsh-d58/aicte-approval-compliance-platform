"use client";
import { useEffect, useRef } from "react";
import { portalLinks } from "@/lib/portal/routes";
import styles from "./ModulesSection.module.css";

const modules = [
  {
    id: "M1",
    name: "Workflow Automation Engine",
    desc: "Routes applications through configurable, sample configured stages with guarded transitions, deficiency returns, and full case history tracking.",
    color: "#F4A200",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07M8.46 8.46a5 5 0 0 0 0 7.07"/>
      </svg>
    ),
  },
  {
    id: "M2",
    name: "Role-Based Dashboards",
    desc: "Tailored views for each stakeholder with workload metrics, ageing indicators, bottleneck alerts, and drill-down to authorised case records.",
    color: "#00897B",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 17h7M17.5 14v7"/>
      </svg>
    ),
  },
  {
    id: "M3",
    name: "EVC Scheduling & Management",
    desc: "Manages EVC queues, committee assignments, smart scheduling against expert availability, invitations, visit tracking, and report generation.",
    color: "#1B6CA8",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>
      </svg>
    ),
  },
  {
    id: "M4",
    name: "Undertaking & Compliance Tracker",
    desc: "Tracks time-bound approval conditions, evidence submissions, verification workflows, escalations, and formal compliance closure.",
    color: "#7B1FA2",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>
      </svg>
    ),
  },
  {
    id: "M5",
    name: "Document Expiry & Renewal Alerts",
    desc: "Maintains a versioned document registry with simulated extraction checks, validity tracking, expiry reminders, renewal workflows, and verification logs.",
    color: "#C62828",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/>
      </svg>
    ),
  },
];

export default function ModulesSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          sectionRef.current?.querySelectorAll(`.${styles.card}`).forEach((el, i) => {
            setTimeout(() => el.classList.add(styles.visible), i * 110);
          });
        }
      },
      { threshold: 0.15 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="modules" className={`section ${styles.modulesSec}`} ref={sectionRef}>
      <div className="container">
        <div className="section-header reveal">
          <span className="eyebrow">Core Modules</span>
          <h2>Five Pillars of Approval Excellence</h2>
          <div className="divider" />
          <p>
            Five proposed modules demonstrated with fictional records and sample rules.
            Approved APH policy and production services remain to be connected.
          </p>
        </div>

        <div className={styles.grid}>
          {modules.map((mod) => (
            <div key={mod.id} className={styles.card} style={{ "--accent-color": mod.color } as React.CSSProperties}>
              <div className={styles.cardTop}>
                <div className={styles.iconWrap} style={{ color: mod.color, background: `${mod.color}18` }}>
                  {mod.icon}
                </div>
                <span className={styles.moduleId}>{mod.id}</span>
              </div>
              <h3 className={styles.cardTitle}>{mod.name}</h3>
              <p className={styles.cardDesc}>{mod.desc}</p>
              <div className={styles.cardFooter}>
                <a href={portalLinks.modules[mod.id as keyof typeof portalLinks.modules]} className={styles.learnMore} style={{ color: mod.color }}>
                  Explore demo
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
