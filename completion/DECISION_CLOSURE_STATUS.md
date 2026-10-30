# Decision and closure repair — 30 October 2026

Policy: planning=deep; context_depth=dependency; verification_depth=impact;
delegation=parallel backend modules with parent frontend/schema/live integration.
Scope: persisted approval conditions and evidence requirements; correct decision
outcomes; explicit closure guards; role/scoped UI; live non-destructive checks.

Observed and repaired: the user's condition is persisted
(0def79df-6df3-401c-ba69-e8a9a1d93c9c) on application
76e9a91b-343a-5d90-8f73-8f96b7b83603. Migration050, validated API fields and the
client now preserve the evidence checklist. The exact PWD attestation and
geotagged-photographs requirements from the supplied script were restored through
the normal scoped PATCH endpoint. The condition remains open, version2.

Approve, Reject and Close now have distinct outcomes. Approval links conditions
and keeps the case open. Closure requires all conditions closed; evidence alone
never closes a case. Institution evidence, independent review, condition closure,
and final case closure were verified against real PostgreSQL with a restricted
runtime connection. All acceptance fixture mutations rolled back.

The decision page lists conditions and requirements, provides a compliance link,
and exposes valid actions only. A successful write followed by failed refresh is
reported as saved, avoiding accidental duplicate creation. Compliance officers
can close verified conditions; application closure remains regional/central.

Verification: 56 affected backend tests, 44 frontend tests, TypeScript, production
build, and 10 live database checks pass. A real Edge test signed in through the
website, opened the decision case, and verified its saved condition/checklist,
compliance link, and unmet-EVC explanation without making a final decision.
Screenshot: storage/qa-decision-closure.png. Logs: tmp/decision-closure-*.log and
tmp/decision-workspace-browser.log.

The previous local API process was hung (health and schema both timed out). Its
workspace-specific process tree was verified and restarted. The live service now
answers health, advertises checklist/PATCH support and returns the restored user
condition. It runs under the existing development auth configuration.

Remaining data dependency: the supplied script's Phase07 visit belongs to another
application. This decision case has no linked EVC visit/report; actual approval is
correctly blocked until its own prerequisites are completed. No final decision,
evidence determination or closure was fabricated on the user's case.

Broader-suite limitation: the initial full regression run also found two failures
outside this repair, in OCR Application-ID parsing semantics and a scanner timeout
expectation changed by other existing edits. These remain recorded in
tmp/decision-closure-backend-tests.log; this report does not claim a clean full
repository suite.

The user's existing case will be read/verified without making its final statutory
decision or closing its obligation automatically. Acceptance mutations use an
isolated labelled demo case inside a rollback transaction.
