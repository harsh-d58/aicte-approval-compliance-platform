# Owner-authorised Phase08 recording preparation

On 30 October 2026 the owner explicitly requested forced approval of the EVC
prerequisite shown on the decision page, leaving final decision recording manual.
This extends the earlier repair's read-only scope for this one synthetic case.

- Application:76e9a91b-343a-5d90-8f73-8f96b7b83603, AICTE-2026-DECISION-001.
- Existing undertaking:0def79df-6df3-401c-ba69-e8a9a1d93c9c, COND-1793341210646.
- Completed demonstration visit: deterministic ID recorded in
  completion/phase8-recording-ready.json.
- Approved source-backed report:d3b8af92-7e0c-42be-b962-ab5351d38d51.

The setup inserts one explicitly labelled completed demo visit with a completion
event, hash-chained audit entry and outbox event. It records no actual inspection
claim. The normal scoped regional API records its submitted demonstration source,
generates the persisted/hash-checked EVC report, submits it for review and approves
it with the owner's recording-only reason. Global workflow guards remain active.
No other application's visit/report was changed.

Final live snapshot checks passed: application Decision pending at decision stage,
original version unchanged, no approval decision or application closure created;
the original condition remains Open with both evidence requirements intact and
no source approval linked yet. The owner must select APPROVE and Record decision.

Evidence: completion/phase8-recording-ready.json and
tmp/phase8-recording-ready.log. Normal Edge sign-in and navigation passed:
APPROVE is selectable, Record decision is enabled, and the existing condition
and checklist remain visible. No final decision was submitted. Screenshot:
storage/qa-phase8-ready.png; log:tmp/phase8-ready-browser.log.
The normal backend APPROVE prerequisite function also passed against this exact
live case, and approval_decisions count remained zero after verification.

VERDICT: PASS
