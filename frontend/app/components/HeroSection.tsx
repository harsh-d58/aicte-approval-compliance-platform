import Image from "next/image";
import footprint from "../../public/footprint.png";
import Icon from "./Icon";
import styles from "./HeroSection.module.css";

export default function HeroSection() {
  return (
    <section id="home" className={styles.hero} aria-labelledby="hero-title">
      <div className={`container ${styles.inner}`}>
        <div className={styles.textCol}>
          <span className={styles.eyebrow}>A unified platform for technical education</span>
          <h1 id="hero-title" className={styles.headline}>
            Simplifying approvals.<br />
            <span>Empowering institutions.</span>
          </h1>
          <p className={styles.subHeadline}>
            A connected approach to AICTE approvals, compliance and expert visits.
            Bringing institutions and decision-makers together, at every step.
          </p>
          <div className={styles.ctaGroup}>
            <a href="#modules" id="hero-explore-btn" className="btn btn-primary">
              Explore the platform <span aria-hidden="true">&rarr;</span>
            </a>
            <a href="#overview" id="hero-workflow-btn" className="btn btn-outline">Platform overview</a>
          </div>
          <div className={styles.features} aria-label="Platform features">
            <span><Icon name="check" size={14} />Transparent processes</span><span><Icon name="check" size={14} />Connected workflows</span><span><Icon name="check" size={14} />Accountable decisions</span>
          </div>
        </div>
        <div className={styles.visualCol}>
          <Image src={footprint}
            alt="Connected government digital services across desktop, tablet and mobile devices"
            className={styles.illustration} sizes="(max-width: 900px) 90vw, 48vw" preload />
        </div>
      </div>
      <div className={styles.bottomNote}>
        <div className={`container ${styles.noteInner}`}>
          <span>AICTE Approval &amp; Compliance Platform</span>
          <a href="#overview">Discover a simpler approval journey <span aria-hidden="true">&darr;</span></a>
        </div>
      </div>
    </section>
  );
}
