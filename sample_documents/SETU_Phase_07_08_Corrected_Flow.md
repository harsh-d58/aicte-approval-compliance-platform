# SETU - corrected Phase07 and Phase08 continuity

The supplied voice-over script contains an inconsistent case caption. Its Phase08
URL is for **AICTE-2026-EVC-001**, the same case as Phase07. The caption
**AICTE-2026-DECISION-001** instead identifies a different application.

Use these linked records to keep the inspection, report and decision on one case:

- Application: AICTE-2026-EVC-001
- Phase07 visit: http://localhost:3000/portal/evc/25800af3-48bf-59b9-b8f7-0ecbb619d2a9
- Current report: http://localhost:3000/portal/meeting-records/8c6023fe-45fb-56eb-b9c3-cf1bb557c353
- Phase08 decision: http://localhost:3000/portal/applications/967bf21d-4e8b-5ec1-a2af-f2f66b2b8a1f/decision

## Current saved state checked on 30 October 2026

The visit remains scheduled for 05 November 2026. Completion has not been recorded.
Report version 4 is submitted and pending approval. Accordingly the application is
still in EVC, and Phase08 final approval is not yet eligible. The original script
omitted recording visit completion before approving the report. Follow the visit
lifecycle after the inspection, then approve the current EVC report as the
authorised regional officer. Verify that the case reaches Decision pending.
Do not describe an unfinished or future inspection as completed for the recording.

## Phase08 - final approval with an open condition

1. As Meera Desai, open the Phase08 decision URL above. Confirm the case number
   is AICTE-2026-EVC-001 and review its approved EVC report.
2. Under Add approval condition, enter:
   - Condition: Submit certified seismic retrofitting compliance for Academic
     Block within 60 days.
   - Required evidence, on separate lines: PWD Structural Safety Attestation;
     Geotagged Photographs.
   - Due: 60 days ahead.
3. Click Create condition once. Confirm it appears in Approval conditions.
4. Under Authorised decision, select APPROVE. Enter the reason after verifying
   it matches the actual approved report: Approved based on successful scrutiny
   and unanimous positive EVC Committee report, subject to seismic condition.
5. Click Record decision. Expected: application Approved; undertaking Open.
6. Nisha can review that same condition in Compliance. The institution must
   submit evidence before an independent compliance determination. Explicit
   condition closure and final application closure are later actions.

## Your separately saved condition

The condition already created in the screenshot belongs to
AICTE-2026-DECISION-001, application 76e9a91b-343a-5d90-8f73-8f96b7b83603.
Its PWD-attestation and geotagged-photographs requirements are saved. It has not
been deleted, duplicated or moved.

**Recording setup update, 30 October 2026:** the owner subsequently requested
forced EVC prerequisite approval for this particular decision case. It now has
an explicitly labelled completed demonstration visit and an approved, source-backed
EVC report. The fixture and report approval are recorded in the audit history;
no actual physical inspection is asserted by the setup. The original Phase07
case and its scheduled visit were left untouched.

For the owner's current Phase08 recording, stay on
http://localhost:3000/portal/applications/76e9a91b-343a-5d90-8f73-8f96b7b83603/decision
and use the condition already saved there. Refresh, select APPROVE, enter the
Phase08 reason, then click Record decision. The preparation itself leaves the
application Decision pending and the undertaking Open.

Condition: http://localhost:3000/portal/compliance/0def79df-6df3-401c-ba69-e8a9a1d93c9c
