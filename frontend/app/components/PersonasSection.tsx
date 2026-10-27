"use client";
import { useEffect, useRef } from "react";
import Icon from "./Icon";
import styles from "./PersonasSection.module.css";

const personas = [
  { icon: <Icon name="institution" />, name: "Institutional Representative", actions: ["Submit applications", "Upload evidence"] },
  { icon: <Icon name="search" />, name: "Scrutiny Officer", actions: ["Review documents", "Issue deficiency notices"] },
  { icon: <Icon name="map" />, name: "Regional Officer", actions: ["Assign cases", "Select EVC experts"] },
  { icon: <Icon name="calendar" />, name: "EVC Coordinator", actions: ["Manage availability", "Track visit completion"] },
  { icon: <Icon name="user" />, name: "EVC Expert", actions: ["Submit availability", "Record observations"] },
  { icon: <Icon name="shield" />, name: "Compliance Officer", actions: ["Verify evidence", "Close conditions"] },
  { icon: <Icon name="institution" />, name: "Central Administrator", actions: ["View aggregate dashboards", "Monitor regions"] },
  { icon: <Icon name="document" />, name: "Policy Administrator", actions: ["Publish workflow versions", "Configure rules"] },
  { icon: <Icon name="shield" />, name: "Auditor", actions: ["Review audit history", "Verify record integrity"] },
  { icon: <Icon name="monitor" />, name: "System Administrator", actions: ["Manage deployments", "Monitor services"] },
];

export default function PersonasSection() {
  const trackRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          sectionRef.current?.querySelectorAll(`.${styles.card}`).forEach((el, i) => {
            setTimeout(() => el.classList.add(styles.visible), i * 60);
          });
        }
      },
      { threshold: 0.15 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="personas" className={`section ${styles.personasSec} bg-subtle`} ref={sectionRef}>
      <div className="container">
        <div className="section-header">
          <span className="eyebrow">Stakeholders</span>
          <h2>Built for Every Role in the Ecosystem</h2>
          <div className="divider" />
          <p>
            Ten distinct personas, each with tailored dashboards, scoped access,
            and role-appropriate workflows designed around the AICTE process.
          </p>
        </div>
      </div>

      {/* Scrollable track — full width */}
      <div className={styles.trackWrapper}>
        <div className={styles.track} ref={trackRef}>
          {personas.map((p) => (
            <div key={p.name} className={styles.card}>
              <div className={styles.cardIcon}>{p.icon}</div>
              <h3 className={styles.cardName}>{p.name}</h3>
              <ul className={styles.actionList}>
                {p.actions.map((a) => (
                  <li key={a}>
                    <span className={styles.dot} />
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
