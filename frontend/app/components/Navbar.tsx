"use client";
import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import styles from "./Navbar.module.css";

const navLinks = [
  { label: "Home", href: "#home" },
  { label: "About", href: "#about" },
  { label: "Modules", href: "#modules" },
  { label: "Workflow", href: "#workflow" },
  { label: "Innovations", href: "#innovations" },
  { label: "Contact", href: "#contact" },
];

export default function Navbar() {
  const menuButton = useRef<HTMLButtonElement>(null);
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      onKeyDown={e => { if (e.key === "Escape" && menuOpen) { setMenuOpen(false); menuButton.current?.focus(); } }}
      id="navbar"
      className={`${styles.navbar} ${scrolled ? styles.scrolled : ""}`}
    >
      <div className={`container ${styles.inner}`}>
        {/* ── Logo Group ── */}
        <a href="#home" className={styles.logoGroup} aria-label="SETU Portal Home">
          <Image
            src="/setu_logo.png"
            alt="SETU Logo"
            width={64}
            height={44}
            unoptimized
            className={styles.setuLogo}
            priority
          />
          <Image
            src="/aicte_logo.png"
            alt="AICTE Logo"
            width={44}
            height={44}
            unoptimized
            className={styles.logoImg}
            priority
          />
          <Image
            src="/moe_logo.svg"
            alt="Ministry of Education Logo"
            width={80}
            height={40}
            className={styles.moeLogo}
            priority
          />
        </a>

        {/* ── Desktop Nav ── */}
        <nav className={styles.desktopNav} aria-label="Main navigation">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href} className={styles.navLink}>
              {link.label}
            </a>
          ))}
        </nav>

        {/* ── CTA ── */}
        <div className={styles.navActions}>
          <a href="/login" id="navbar-login-btn" className={`btn ${styles.ctaBtn}`}>
            Login to Portal
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </a>
          {/* Hamburger */}
          <button
            ref={menuButton}
            id="navbar-hamburger"
            className={styles.hamburger}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
          >
            <span className={`${styles.bar} ${menuOpen ? styles.bar1Open : ""}`} />
            <span className={`${styles.bar} ${menuOpen ? styles.bar2Open : ""}`} />
            <span className={`${styles.bar} ${menuOpen ? styles.bar3Open : ""}`} />
          </button>
        </div>
      </div>

      {/* ── Mobile Menu ── */}
      <div id="mobile-navigation" hidden={!menuOpen} className={`${styles.mobileMenu} ${menuOpen ? styles.mobileMenuOpen : ""}`}>
        {navLinks.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className={styles.mobileLink}
            onClick={() => setMenuOpen(false)}
          >
            {link.label}
          </a>
        ))}
        <a href="/login" className={`btn ${styles.mobileCta}`} onClick={() => setMenuOpen(false)}>
          Login to Portal
        </a>
      </div>
    </header>
  );
}
