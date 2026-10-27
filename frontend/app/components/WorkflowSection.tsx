"use client";
import { useState, useEffect, useRef } from "react";
import Icon from "./Icon";
import styles from "./WorkflowSection.module.css";

const steps = [
  {
    id: "DRAFT",
    label: "Draft",
    icon: <Icon name="document" />,
    color: "#78909C",
    detail:
      "Institution prepares the application with required documents and institutional information. Applicable deadlines depend on the approved policy; this prototype uses sample values.",
  },
  {
    id: "SUBMITTED",
    label: "Submitted",
    icon: <Icon name="send" />,
    color: "#1B6CA8",
    detail:
      "Authorised institutional representative formally submits the application. A unique application number is assigned and the process clock starts.",
  },
  {
    id: "IN_REVIEW",
    label: "In Review",
    icon: <Icon name="search" />,
    color: "#F4A200",
    detail:
      "Assigned scrutiny officer reviews documents, verifies compliance with APH criteria, and records observations. SLA countdown is active.",
  },
  {
    id: "RETURNED_FOR_DEFICIENCY",
    label: "Deficiency Return",
    icon: <Icon name="alert" />,
    color: "#C62828",
    detail:
      "Scrutiny officer issues a deficiency notice with specific items. The institution has a prescribed window to respond and resubmit.",
  },
  {
    id: "AWAITING_EVC",
    label: "Awaiting EVC",
    icon: <Icon name="calendar" />,
    color: "#7B1FA2",
    detail:
      "Application requires an Expert Visit Committee inspection. The EVC queue is activated and the scheduling workflow begins.",
  },
  {
    id: "AWAITING_COMPLIANCE",
    label: "Compliance Pending",
    icon: <Icon name="shield" />,
    color: "#00695C",
    detail:
      "Post-approval undertakings are being tracked. Institution must submit evidence within prescribed timelines.",
  },
  {
    id: "APPROVED",
    label: "Approved",
    icon: <Icon name="check" />,
    color: "#2E7D32",
    detail:
      "Formal approval decision recorded by the authorised decision-making authority. Approval letter and compliance conditions are issued.",
  },
];
const approval = steps.pop()!;
steps.splice(4, 0, { id: "RESUBMITTED", label: "Resubmitted", icon: <Icon name="document" />, color: "#1B6CA8", detail: "If deficiencies are returned, the institution submits corrected evidence versions for scrutiny before the optional EVC route." });
steps.splice(6, 0, { id: "DECISION_PENDING", label: "Decision", icon: <Icon name="shield" />, color: "#183b61", detail: "The authorised authority records approval or rejection after the configured review route. EVC reports require human approval where applicable." }, approval);
steps.push({id:"CLOSED",label:"Closed",icon:<Icon name="check"/>,color:"#2E7D32",detail:"After approval and any required verified conditions, the authorised officer closes the case with a recorded reason. Rejection and withdrawal are separate terminal outcomes."});

export default function WorkflowSection() {
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          sectionRef.current?.querySelectorAll(`.${styles.step}`).forEach((el, i) => {
            setTimeout(() => el.classList.add(styles.visible), i * 80);
          });
        }
      },
      { threshold: 0.2 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="workflow" className={`section ${styles.workflowSec}`} ref={sectionRef}>
      <div className="container">
        <div className="section-header">
          <span className="eyebrow">Application Lifecycle</span>
          <h2>How an Application Flows</h2>
          <div className="divider" />
          <p>
            From initial draft to final approval — every stage is tracked,
            assigned, and governed by a sample configurable workflow. Deficiency returns loop through resubmission; EVC and post-approval conditions apply only when required.
          </p>
        </div>

        {/* Stepper */}
        <div className={styles.stepper}>
          {steps.map((step, i) => (
            <div key={step.id} className={styles.stepWrapper}>
              <button
                id={`workflow-step-${step.id.toLowerCase()}`}
                className={`${styles.step} ${activeStep === i ? styles.stepActive : ""}`}
                onClick={() => setActiveStep(activeStep === i ? null : i)}
                style={{ "--step-color": step.color } as React.CSSProperties}
                aria-expanded={activeStep === i}
                aria-controls="workflow-detail"
              >
                <div className={styles.stepIcon}>{step.icon}</div>
                <div className={styles.stepLabel}>{step.label}</div>
                <div className={styles.stepId}>{step.id}</div>
              </button>
              {i < steps.length - 1 && (
                <div className={`${styles.connector} ${i < (activeStep ?? -1) ? styles.connectorActive : ""}`} />
              )}
            </div>
          ))}
        </div>

        {/* Detail panel */}
        {activeStep !== null && (
          <div
            id="workflow-detail"
            role="region"
            aria-label="Selected workflow stage"
            className={styles.detailPanel}
            style={{ borderColor: steps[activeStep].color + "44", "--step-color": steps[activeStep].color } as React.CSSProperties}
          >
            <div className={styles.detailIcon}>{steps[activeStep].icon}</div>
            <div>
              <div className={styles.detailStatus}>
                <span className={styles.detailBadge} style={{ background: steps[activeStep].color + "22", color: steps[activeStep].color }}>
                  {steps[activeStep].id}
                </span>
                <h3 className={styles.detailTitle}>{steps[activeStep].label}</h3>
              </div>
              <p className={styles.detailDesc}>{steps[activeStep].detail}</p>
            </div>
          </div>
        )}

        {!activeStep && activeStep !== 0 && (
          <p className={styles.clickHint}>Select any stage above to see details</p>
        )}
      </div>
    </section>
  );
}
