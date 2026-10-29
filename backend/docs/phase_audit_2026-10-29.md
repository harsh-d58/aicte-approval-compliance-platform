# Phase/PRD integration audit — 29 October 2026

This is a source and contract audit, not a certification that every phase passes
its end-to-end gate. The implementation plan has nine numbered sections, while
the brief groups delivery into seven phases. Those groupings describe overlapping
work and are not seven or nine independent proofs of completion.

| Area | Observed implementation | Gap found in this audit |
| --- | --- | --- |
| Identity | Supabase Auth and persisted assignments | Original full portal consumed local demo identities; backend authorization must accompany live adaptation. Supabase sign-in alone conveys no regulatory permissions. |
| Institution/application | Draft, submit, transition, deficiency and decision routes | Full UI previously called local `applyCommand`; several UI mutations had no matching API. Institution creation and assignment/status supplements now exist, pending live journey proof. |
| Documents/OCR | Metadata, local storage helper, advisory OCR/check routes | Original UI kept binary files in IndexedDB; upload session endpoint did not accept browser binary content. Seeded document metadata cannot prove an original file or OCR result exists. |
| EVC | Selection, recommendation, confirmation, completion routes | Original expert-only availability omitted institution availability; confirmation rules and cancellation/postponement/invitations require live validation. Additive migration 010 supplies institution availability. |
| Meeting records/compliance | Draft/review/approval, evidence/verification/closure routes | Draft generation stores a content reference; editing needs real persisted sections. Supplemental record editing stores source-linked sections and new immutable versions. |
| Notifications/workers | Persisted logical notifications, attempts, outbox helpers | HTTP processing helpers do not establish that Redis/Celery workers run continuously or that real email/SMS/calendar delivery occurs. `job.process` deliberately cannot fabricate completion. |
| Dashboards/eight reports | SQL aggregate/report handlers; rich frontend analytics | Rich portal previously derived all metrics from fixtures. Backend report filters, actor scope and distinct-case aggregation need reconciliation against the same live snapshot used by dashboards. |
| Configuration/admin | Read endpoints plus frontend editors | Workflow writes and selected supplemental commands now persist. Some typed catalogue editors remain unsupported; generic setting writes must not impersonate published APH/document/notification policy. |
| Operations/pilot | Verification scripts and documentation | Source scripts and unit tests cannot establish backup restoration, load targets, external anchoring, real provider delivery, pilot acceptance or rollout approval. |

## Command adapter coverage

`frontend/lib/live/commands.ts` maps supported UI commands to existing FastAPI
contracts and delegates supplemental mutations to `/portal/commands`. No successful
live action runs the browser `applyCommand` reducer. Unsupported actions return an
error rather than writing a fictional success to session storage.

`backend/app/portal_commands.py` supplements notification read, institution creation,
application assignment/status/migration, renewal submission/verification,
institution availability, visit postponement/cancellation, invitation responses,
observation editing, action items, source-linked meeting record editing, workflow
draft/version publication, selected settings/committee configuration, user status
and role assignments, job retry, and connector disabling. It takes a scoped
server snapshot inside the write transaction and checks persisted roles and
record visibility; audit and outbox entries are part of that transaction.

Remaining explicit gaps: real connector connection tests and worker processing;
typed APH/document/notification/escalation configuration writers; complete
deficiency narrative and exact-version response persistence; direct backend
submission validation of every mandatory document and declared academic year;
governance/approval semantics beyond the prototype policy. These should stay open
in the full-scale plan until executable acceptance journeys prove them.

## Verification observed for the supplement

- TypeScript `tsc --noEmit`: exit 0 after creating the bridge.
- Python compilation of `portal_commands.py`: exit 0.
- `python -m unittest backend.tests.test_portal_commands -v`: 7 tests passed;
  own-recipient enforcement, wrong-role denial, hidden records, stale versions,
  unsupported actions, and persisted notification-read SQL.

Live database mutation/reload evidence and full regression evidence are recorded
by the parent integration task separately. These unit checks do not establish
that every SQL branch or UI workflow has been exercised live.
