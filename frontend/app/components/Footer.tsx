"use client";
import Image from "next/image";
import styles from "./Footer.module.css";

const quickLinks = [
  { label: "Home", href: "#home" },
  { label: "About", href: "#about" },
  { label: "Modules", href: "#modules" },
  { label: "Workflow", href: "#workflow" },
  { label: "Innovations", href: "#innovations" },
];

const legalLinks = [
  { label: "Privacy Policy", href: "/privacy" },
  { label: "Accessibility", href: "/accessibility" },
  { label: "Website Policies", href: "/website-policies" },
  { label: "Sitemap", href: "/sitemap" },
];

export default function Footer() {
  const year = "2026";
  const lastUpdated = "26 October 2026";

  return (
    <footer className={styles.footer}>
      {/* Top section */}
      <div className={`container ${styles.topSection}`}>
        {/* Col 1: Branding */}
        <div className={styles.brandCol}>
          <div className={styles.logoRow}>
            <Image src="/aicte_logo.png" alt="AICTE Logo" width={380} height={73} unoptimized className={styles.footerAicteLogo} />
            <Image src="/moe_logo.svg" alt="Ministry of Education" width={80} height={36} className={styles.footerMoeLogo} />
          </div>
          <p className={styles.brandTitle}>AICTE Approval Workflow Platform</p>
          <p className={styles.brandTagline}>
            Empowering Technical Education in India through transparent,
            automated, and compliant institutional governance.
          </p>
          <div className={styles.govTag}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z"/><circle cx="12" cy="10" r="3"/></svg>
            Student demonstration · fictional data
          </div>
        </div>

        {/* Col 2: Quick Links */}
        <div className={styles.linksCol}>
          <h4 className={styles.colTitle}>Quick Links</h4>
          <ul className={styles.linkList}>
            {quickLinks.map((l) => (
              <li key={l.label}>
                <a href={l.href} className={styles.footerLink}>
                  <span className={styles.linkArrow}>›</span>
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Col 3: Legal */}
        <div className={styles.linksCol}>
          <h4 className={styles.colTitle}>Legal &amp; Policies</h4>
          <ul className={styles.linkList}>
            {legalLinks.map((l) => (
              <li key={l.label}>
                <a href={l.href} className={styles.footerLink}>
                  <span className={styles.linkArrow}>›</span>
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Col 4: Contact */}
        <div className={styles.contactCol}>
          <h4 className={styles.colTitle}>Contact</h4>
          <p className={styles.contactText}>
            Prototype support &amp; guidance<br /><a href="/help">Read the demonstration guide →</a>
          </p>
          <div className={styles.disclaimer}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            This is a prototype. Not an official AICTE portal.
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className={styles.footerDivider} />

      {/* Bottom bar */}
      <div className={`container ${styles.bottomBar}`}>
        <p className={styles.copyright}>
          © {year} Student prototype · Not an official government service
        </p>
        <p className={styles.lastUpdated}>
          Last updated: {lastUpdated}
        </p>
      </div>
    </footer>
  );
}
