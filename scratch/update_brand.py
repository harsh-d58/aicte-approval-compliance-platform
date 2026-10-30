with open("frontend/app/portal-ui/ui.tsx", "r", encoding="utf-8") as f:
    text = f.read()

target = """export function Brand({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className={s.brand} aria-label="AICTE Portal home"><Image src="/aicte_logo.png" alt="" width={46} height={46} unoptimized className={s.brandLogo} /><span><strong>AICTE Portal</strong><small>{compact ? "Approval & compliance" : "Approval & Compliance Platform"}</small></span></Link>;
}"""

replacement = """export function Brand({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className={s.brand} aria-label="SETU Portal home"><Image src="/setu_logo.png" alt="SETU Logo" width={48} height={48} unoptimized className={s.brandLogo} /><span><strong>SETU Portal</strong><small>{compact ? "Approval & compliance" : "Approval & Compliance Platform"}</small></span></Link>;
}"""

text_norm = text.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
replacement_norm = replacement.replace("\r\n", "\n")

assert target_norm in text_norm, "Target not found"
text_norm = text_norm.replace(target_norm, replacement_norm, 1)

with open("frontend/app/portal-ui/ui.tsx", "w", encoding="utf-8") as f:
    f.write(text_norm)

print("Updated ui.tsx successfully!")

