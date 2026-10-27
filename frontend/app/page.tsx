import Navbar from "./components/Navbar";
import HeroSection from "./components/HeroSection";
import StatsBar from "./components/StatsBar";
import OverviewSection from "./components/OverviewSection";
import ModulesSection from "./components/ModulesSection";
import InnovationsSection from "./components/InnovationsSection";
import WorkflowSection from "./components/WorkflowSection";
import PersonasSection from "./components/PersonasSection";
import CTASection from "./components/CTASection";
import Footer from "./components/Footer";

export default function Home() {
  return (
    <>
      <Navbar />
      <main id="main-content">
        <HeroSection />
        <StatsBar />
        <OverviewSection />
        <ModulesSection />
        <InnovationsSection />
        <WorkflowSection />
        <PersonasSection />
        <CTASection />
      </main>
      <Footer />
    </>
  );
}
