import { DemoProvider } from "@/app/portal-ui/DemoProvider";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <DemoProvider>{children}</DemoProvider>;
}
