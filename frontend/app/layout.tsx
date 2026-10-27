import type { Metadata } from "next";
import { Noto_Sans } from "next/font/google";
import "./globals.css";

const notoSans = Noto_Sans({
  subsets: ["latin"],
  variable: "--font-noto-sans",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AICTE Approval Workflow Platform | Institutional Compliance Monitoring",
  description:
    "An integrated platform for AICTE approval workflow automation, institutional compliance monitoring, EVC scheduling, and document management for technical institutions across India.",
  keywords: [
    "AICTE",
    "approval workflow",
    "institutional compliance",
    "EVC scheduling",
    "technical education",
    "Ministry of Education",
  ],
  openGraph: {
    title: "AICTE Approval Workflow Automation Platform",
    description:
      "Streamlining AICTE approvals and empowering institutions with automated compliance monitoring.",
    type: "website",
    locale: "en_IN",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={notoSans.variable}>
      <body><a href="#main-content" className="skip-link">Skip to main content</a>{children}</body>
    </html>
  );
}
