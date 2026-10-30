with open("frontend/app/components/Navbar.tsx", "r", encoding="utf-8") as f:
    text = f.read()

target = """        {/* ── Logo Group ── */}
        <a href="#home" className={styles.logoGroup} aria-label="AICTE Portal Home">
          <Image
            src="/aicte_logo.png"
            alt="AICTE Logo"
            width={380}
            height={73}
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
          <div className={styles.logoText}>
            <span className={styles.logoTitle}>AICTE Portal</span>
            <span className={styles.logoSub}>Approval &amp; Compliance Platform</span>
          </div>
        </a>"""

replacement = """        {/* ── Logo Group ── */}
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
          <div className={styles.logoText}>
            <span className={styles.logoTitle}>SETU</span>
            <span className={styles.logoSub}>AICTE Approval &amp; Compliance</span>
          </div>
        </a>"""

text_norm = text.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
replacement_norm = replacement.replace("\r\n", "\n")

assert target_norm in text_norm, "Target not found in Navbar.tsx"
text_norm = text_norm.replace(target_norm, replacement_norm, 1)

with open("frontend/app/components/Navbar.tsx", "w", encoding="utf-8") as f:
    f.write(text_norm)
print("Updated Navbar.tsx successfully!")

