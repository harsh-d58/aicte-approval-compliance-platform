# Login and Phase08 repair

Policy: compact planning, dependency context, impact verification, delegated
read-only backend diagnosis and a bounded login-page fix. Parent owns session
restore, request bounding, snapshot refresh and Phase08 reconciliation.

Acceptance:
- Original ten demo card keys remain compatible with the prototype endpoint.
- Supabase password authentication is retained.
- Old restoration/refresh responses cannot replace or clear a newer login.
- A stalled identity/snapshot request ends with a recoverable message.
- Duplicate focus/poll reads for the same session are coalesced.
- Normal demo login, reload, sign-out and role switching work in the browser.
- Phase08 links and labels refer to the actual Phase07 application. Existing
  conditions and real workflow prerequisites are preserved.

Decision: fix session races and bounded reads because LiveProvider restoration
clears storage even after cleanup, reads have no deadline, and DemoProvider
starts parallel snapshot reads on focus/poll. LoginPage also substitutes database
UUIDs for the stable prototype card keys when the directory includes ten roles.
No statutory decisions or inspection approvals are authorised by these repairs.

Implemented: stable demo card IDs; visible retry controls after errors; generation
guards for restoration/login/sign-out; a shared Supabase token refresh; bounded
identity and snapshot reads including response consumption; coalesced polling and
focus reads; fresh reads after committed writes; rejection of obsolete success
and error responses. Public/login routes do not start dashboard polling. Dynamic
route tracking is isolated behind Suspense, preserving production prerendering.
Supabase password sign-in and server permissions remain in use.

Tests reproduced and fixed two additional defects: sign-out during pending
profile validation left loading true, and an older failed snapshot hid a newer
valid workspace. The six focused login/session tests now pass, as do all44
existing frontend tests and the production build (including TypeScript).

Actual Edge verification after the final provider changes: regional login19s,
full reload restored the session, central login23s, return to regional25s, and
sign-out cleared the browser session. All relevant API responses were200; no
JavaScript page errors. These are measured successful development timings, not
an instant-login claim. Real password sign-in with a user's credentials was not
attempted; its timeout and request behavior are covered by isolated tests, and
the real Supabase JWKS endpoint responded successfully.

Phase08 reconciliation: the attachment's URL uses application967bf21d..., the
same case as Phase07 (AICTE-2026-EVC-001). Its caption instead names another
case, AICTE-2026-DECISION-001 (76e9a91b...), which is in the user's screenshot.
The latter's saved condition was preserved. The former's visit25800af3... is
still scheduled05November2026, not completed; report8c6023fe... v4 remains
pending approval. Neither case is eligible to bypass inspection/report review.

Decision UI now retains the decision controls visibly disabled with the actual
blocker and links to that same application's visits/reports. An empty history
says no decision was recorded, instead of suggesting a filter/scope problem.
The saved condition/checklist and disabled button were verified through normal
website navigation. The corrected guide is
sample_documents/SETU_Phase_07_08_Corrected_Flow.md.

Evidence: tmp/login-session-tests.log, tmp/login-portal-regression.log,
tmp/login-phase8-build.log, tmp/login-live-browser.log,
tmp/phase8-browser.log, storage/qa-decision-closure.png.

VERDICT: PASS
