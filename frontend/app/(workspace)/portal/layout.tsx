import PortalShell from "@/app/portal-ui/PortalShell";
import { Suspense } from "react";
import { Loading } from "@/app/portal-ui/ui";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Your workspace | AICTE Portal" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<Loading />}>
      <PortalShell>{children}</PortalShell>
    </Suspense>
  );
}
