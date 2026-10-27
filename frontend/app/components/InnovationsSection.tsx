"use client";
import { useEffect, useRef } from "react";
import Link from "next/link";
import styles from "./InnovationsSection.module.css";

export default function InnovationsSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          sectionRef.current?.querySelectorAll(`.${styles.card}`).forEach((el, i) => {
            setTimeout(() => el.classList.add(styles.visible), i * 200);
          });
        }
      },
      { threshold: 0.2 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="innovations" className={`section bg-hero-gradient ${styles.section}`} ref={sectionRef}>
      {/* Decorative circles */}
      <div className={styles.deco1} />
      <div className={styles.deco2} />

      <div className="container" style={{ position: "relative", zIndex: 1 }}>
        <div className="section-header">
          <span className="eyebrow" style={{ color: "#803009" }}>Proposed Innovations</span>
          <h2 style={{ color: "var(--text-primary)" }}>Two Innovations Setting Us Apart</h2>
          <div className="divider" />
          <p style={{ color: "var(--text-muted)" }}>
            Two proposed platform capabilities support traceability and coordination.
            This prototype demonstrates local fingerprints and source-linked draft records.
          </p>
        </div>

        <div className={styles.grid}>
          {/* ── Innovation 1: Blockchain Audit ── */}
          <div className={styles.card}>
            <div className={styles.cardAccentBar} style={{ background: "linear-gradient(180deg, #7C4DFF, #4527A0)" }} />
            <div className={styles.cardInner}>
              <div className={styles.iconCircle} style={{ background: "rgba(124,77,255,0.15)", border: "1px solid rgba(124,77,255,0.3)" }}>
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#9575CD" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="7" width="6" height="6" rx="1"/><rect x="16" y="7" width="6" height="6" rx="1"/>
                  <rect x="9" y="3" width="6" height="6" rx="1"/><rect x="9" y="15" width="6" height="6" rx="1"/>
                  <line x1="8" y1="10" x2="9" y2="10"/><line x1="15" y1="10" x2="16" y2="10"/>
                  <line x1="12" y1="9" x2="12" y2="15"/>
                </svg>
              </div>
              <div className={styles.badge} style={{ background: "rgba(124,77,255,0.15)", border: "1px solid rgba(124,77,255,0.3)", color: "#624198" }}>
                Innovation 1
              </div>
              <h3 className={styles.cardTitle}>Record Integrity &amp; Optional Audit Anchoring</h3>
              <p className={styles.cardDesc}>
                The proposed production audit layer would anchor selected event fingerprints.
                This demonstration compares local SHA-256 fingerprints only; no ledger is
                connected, and a fingerprint does not certify document authenticity.
              </p>

              {/* Visual: Chain nodes */}
              <div className={styles.chainViz}>
                {["Genesis", "Application\nSubmitted", "EVC\nScheduled", "Approved"].map((label, i) => (
                  <div key={i} className={styles.chainGroup}>
                    <div className={styles.chainNode}>
                      <div className={styles.chainHash}>#{(0xA1B2 + i * 0x3F7).toString(16).toUpperCase()}</div>
                    </div>
                    <div className={styles.chainLabel}>{label}</div>
                    {i < 3 && <div className={styles.chainConnector} />}
                  </div>
                ))}
              </div>

              <ul className={styles.bulletList}>
                <li>Proposed append-only audit service</li>
                <li>Optional Hyperledger Fabric anchoring</li>
                <li>Local demonstration uses fictional data</li>
              </ul><Link href="/portal/audit/verify">Explore integrity demonstration →</Link>
            </div>
          </div>

          {/* ── Innovation 2: EVC AI Assistant ── */}
          <div className={styles.card}>
            <div className={styles.cardAccentBar} style={{ background: "linear-gradient(180deg, #F4A200, #E65100)" }} />
            <div className={styles.cardInner}>
              <div className={styles.iconCircle} style={{ background: "rgba(244,162,0,0.15)", border: "1px solid rgba(244,162,0,0.3)" }}>
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#F4A200" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  <path d="M8 10h8M8 14h5"/>
                </svg>
              </div>
              <div className={styles.badge} style={{ background: "rgba(244,162,0,0.12)", border: "1px solid rgba(244,162,0,0.3)", color: "#803009" }}>
                Innovation 2
              </div>
              <h3 className={styles.cardTitle}>EVC Committee Coordination &amp; Meeting-to-Record Assistant</h3>
              <p className={styles.cardDesc}>
                In this demonstration, an officer selects the configured sample committee.
                Manual availability produces explainable slot recommendations. Submitted
                observations become source-linked minutes and EVC-report drafts for human
                review; external calendars and AI transcription remain disconnected.
              </p>

              {/* Visual: Timeline */}
              <div className={styles.timeline}>
                {[
                  { step: "1", label: "Expert Selection", sub: "Officer selects 4–5 experts" },
                  { step: "2", label: "Slot Recommendation", sub: "System finds common availability" },
                  { step: "3", label: "Meeting Conducted", sub: "Visit & observations recorded" },
                  { step: "4", label: "Draft Report", sub: "Auto-generated for committee review" },
                ].map((item) => (
                  <div key={item.step} className={styles.timelineItem}>
                    <div className={styles.timelineStep}>{item.step}</div>
                    <div>
                      <div className={styles.timelineLabel}>{item.label}</div>
                      <div className={styles.timelineSub}>{item.sub}</div>
                    </div>
                  </div>
                ))}
              </div><Link href="/portal/evc">Explore expert visits →</Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
