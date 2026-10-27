export default function PendingPortal({ children, fallback }: { children: React.ReactNode; fallback: React.ReactNode }) {
  // Keep the nested route in React's render tree during client-only session bootstrap.
  // Pages already guard missing scoped data; hide their output until the shell is ready.
  // Omitting children here prevents Next.js from validating the page's navigation shell.
  return <>{fallback}<div hidden inert>{children}</div></>;
}
