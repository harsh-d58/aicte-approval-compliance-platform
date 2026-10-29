import { DemoProvider } from "@/app/portal-ui/DemoProvider";
import { LiveProvider } from "@/app/portal-ui/LiveProvider";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <LiveProvider>
      <DemoProvider>{children}</DemoProvider>
    </LiveProvider>
  );
}
