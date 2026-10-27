"use client";
import { useEffect, useRef } from "react";
import styles from "./CTASection.module.css";

export default function CTASection() {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) ref.current?.classList.add(styles.visible);
      },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="contact" className={`${styles.ctaSec} bg-hero-gradient-flipped`} ref={ref}>
      {/* Particle dots */}
      <div className={styles.particles}>
        {[
          { left: "12%", top: "22%", delay: "0.5s", duration: "4.2s", size: "4px" },
          { left: "84%", top: "15%", delay: "1.2s", duration: "5.1s", size: "5px" },
          { left: "35%", top: "78%", delay: "2.1s", duration: "3.8s", size: "3px" },
          { left: "72%", top: "65%", delay: "0.8s", duration: "6.0s", size: "6px" },
          { left: "18%", top: "82%", delay: "2.8s", duration: "4.5s", size: "4px" },
          { left: "91%", top: "48%", delay: "1.6s", duration: "5.5s", size: "5px" },
          { left: "50%", top: "12%", delay: "3.1s", duration: "4.0s", size: "3px" },
          { left: "63%", top: "88%", delay: "0.4s", duration: "5.8s", size: "5px" },
          { left: "28%", top: "45%", delay: "2.3s", duration: "4.7s", size: "4px" },
          { left: "80%", top: "75%", delay: "1.9s", duration: "3.9s", size: "6px" },
          { left: "8%", top: "60%", delay: "0.7s", duration: "5.2s", size: "3px" },
          { left: "42%", top: "30%", delay: "2.5s", duration: "4.4s", size: "5px" },
          { left: "95%", top: "28%", delay: "1.1s", duration: "6.2s", size: "4px" },
          { left: "60%", top: "52%", delay: "3.4s", duration: "4.1s", size: "3px" },
          { left: "22%", top: "18%", delay: "1.4s", duration: "5.0s", size: "5px" },
          { left: "75%", top: "38%", delay: "2.7s", duration: "4.8s", size: "4px" },
        ].map((p, i) => (
          <div
            key={i}
            className={styles.particle}
            style={{
              left: p.left,
              top: p.top,
              animationDelay: p.delay,
              animationDuration: p.duration,
              width: p.size,
              height: p.size,
            }}
          />
        ))}
      </div>

      <div className={`container ${styles.inner}`}>
        <div className={styles.content}>
          <h2 className={styles.headline}>
            Ready to Transform<br />
            <span className={styles.highlight}>Institutional Compliance?</span>
          </h2>
          <p className={styles.subtext}>
            Join the platform designed for AICTE&apos;s approval ecosystem —
            automating what can be automated, while keeping humans in control of what matters.
          </p>

          <div className={styles.ctaGroup}>
            <a href="/login" id="cta-access-btn" className={`btn btn-primary ${styles.ctaBtn}`}>
              Explore demo
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </a>
            <a href="#modules" id="cta-explore-btn" className={`btn btn-outline-light`}>
              Explore Modules
            </a>
          </div>

          {/* Key points */}
          <div className={styles.pointsRow}>
            {[
              "Sample APH workflows",
              "Traceable demo history",
              "Smart EVC scheduling",
              "Role-based access control",
            ].map((pt) => (
              <div key={pt} className={styles.point}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4DB6AC" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span>{pt}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
