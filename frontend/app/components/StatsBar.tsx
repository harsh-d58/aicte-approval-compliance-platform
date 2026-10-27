"use client";
import { useEffect, useRef } from "react";
import Icon from "./Icon";
import styles from "./StatsBar.module.css";

const stats = [
  { value: 3, suffix: "", label: "Sample Institutions", icon: <Icon name="institution" /> },
  { value: 5, suffix: "", label: "Planned Core Modules", icon: <Icon name="settings" /> },
  { value: 8, suffix: "", label: "Report Categories", icon: <Icon name="monitor" /> },
  { value: 2, suffix: "", label: "Prototype Innovations", icon: <Icon name="check" /> },
];

function animateCounter(el: HTMLElement, target: number, duration = 1800) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = target.toLocaleString("en-IN"); return; }
  let start = 0;
  const step = (timestamp: number) => {
    if (!start) start = timestamp;
    const progress = Math.min((timestamp - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.floor(ease * target).toLocaleString("en-IN");
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target.toLocaleString("en-IN");
  };
  requestAnimationFrame(step);
}

export default function StatsBar() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const animated = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !animated.current) {
          animated.current = true;
          const counters = sectionRef.current?.querySelectorAll<HTMLElement>("[data-count]");
          counters?.forEach((el) => {
            const target = parseInt(el.dataset.count ?? "0", 10);
            animateCounter(el, target);
          });
          sectionRef.current?.querySelectorAll(`.${styles.statItem}`).forEach((el, i) => {
            setTimeout(() => el.classList.add(styles.visible), i * 100);
          });
        }
      },
      { threshold: 0.3 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="about" className={`${styles.statsBar}`} ref={sectionRef}>
      <div className={`container ${styles.inner}`}>
        {stats.map((s) => (
          <div key={s.label} className={styles.statItem}>
            <div className={styles.iconCircle}>{s.icon}</div>
            <div className={styles.valRow}>
              <span
                className={styles.value}
                data-count={s.value}
              >
                0
              </span>
              <span className={styles.suffix}>{s.suffix}</span>
            </div>
            <span className={styles.label}>{s.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
