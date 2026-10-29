# Identity, roles and scope — detailed P0 plan

Source: [PRD v1.0](<Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md>) §§3, 5.2, 9.1–9.2, 12–13, 17.5 and 21. This expands the first open item in [tech_stack_plan.md](tech_stack_plan.md) and B02 in [fastapi_plan.md](fastapi_plan.md). Updated **29 October 2026**.

**Outcome:** a real authorised user can sign in, see only records allowed by an approved role **and** scope, and lose that access promptly when disabled or revoked. Privileged operations are enforced by FastAPI and audited. No user receives regulatory access merely by authenticating, entering an institution code or selecting a browser role.

**Policy boundary:** The PRD proposes Keycloak for the prototype (§4.2); the user selected Supabase Auth instead. Supabase proves identity; `public.users`, `roles`, `permissions`, `role_permissions` and `user_role_assignments` remain authoritative for application access. PRD personas and example actions are a starting catalogue, **not an approved grant matrix**. No official role, permission or user records have been inserted; [synthetic institutions and cases](backend/docs/mock_dataset.md) are labelled DEMO.

The concrete review template is [access_policy_decisions.md](backend/docs/access_policy_decisions.md). Its open fields must be decided and signed off before any live grant is provisioned.

A minimal [test-only read policy](backend/docs/prototype_access_proposal.md) was approved by the project owner. One confirmed Supabase account is provisioned with `institution.read` and `application.read` on `DEMO-INST-0001`; its database read scope and audit evidence passed checks. The broader official policy is still open.

## 0. Verified starting point

- [x] The single ignored root `.env` has the Supabase project URL and publishable key; the public Auth settings endpoint accepted the key. Database connectivity works over TLS in a read-only transaction.
- [x] FastAPI checks Supabase access-token signature against project JWKS, issuer, audience, expiry, issue time, user/session identifiers, `authenticated` role and non-anonymous status.
- [x] `GET /api/v1/me` and `/me/permissions` resolve an active application user and active, time-valid assignments. Four institution/application list/detail routes check permission and scope in SQL.
- [x] Read queries now use the database's lowercase `active` status and scope values. The backend regression suite checks this contract; it is not yet a real-user access test.
- [x] Unknown and out-of-scope detail IDs both return 404 in the current read API; unauthenticated `/me` returns 401. The frontend live shell sends a bearer token and does not grant access from its old fictional role picker.
- [x] Exercise the positive live browser path: the signed-in session reached `/me`, `/institutions` and `/applications`, and all three returned 200. The approved DEMO assignment exists; direct database checks saw exactly one institution and six applications.
- [ ] Exercise real-token out-of-scope detail requests and revocation. Direct database calls returned 404 for other details, but browser-token denial and revocation are not yet tested.

## 1. Approval package before provisioning (§§3, 13.1, 21)

Prepare one versioned policy artifact signed off by the authorised policy and security owners. It should state:

- [ ] **Role catalogue:** confirm which of the PRD §3.1 personas become application roles, their exact names/codes and who may hold multiple roles. Include institutional representative, scrutiny officer, regional officer, EVC coordinator, EVC expert, compliance officer, central administrator, policy/configuration administrator, auditor, system administrator and integration service as candidates for review, not automatic grants.
- [ ] **Action matrix:** for each role/resource pair, approve Read, Create, Update, Assign, Transition, Return, Verify, Approve, Configure, Export and Administer actions from PRD §3.3. Separate view permission from file download, report export, verification and statutory approval.
- [ ] **Scope matrix:** approve permitted `global`, `region`, `institution`, `application` and `campus` assignments for each role; define how an assigned case, expert membership and compliance responsibility grant access. `global` must require explicit authority. The database has no `evc` scope type; visit access needs a separate approved membership rule.
- [ ] **Region hierarchy:** decide whether a region grant includes only records whose institution has that direct `region_id` or descendants too. Current read SQL implements direct region matching only.
- [ ] **Grant lifecycle:** define who can grant/change/revoke assignments; required reason and approval; start/end timestamps; duplicate/overlap policy; maximum scope; emergency access; and how quickly disable/revocation must take effect.
- [ ] **Identity lifecycle:** define account invitation/verification, disabled users, lost access, role transfer, offboarding, service identities and whether privileged actions require stronger authentication.
- [ ] **Segregation of duties:** specify incompatible combinations and human approval boundaries. System administration must not automatically imply statutory decision power; auditors should not alter workflow state; the scheduler must not select EVC experts.
- [ ] **Evidence and retention:** approve audit fields, access-review cadence, grant history retention and minimal personal data collected for identity administration.

**Approval gate:** a named policy owner has approved the versioned role/action/scope matrix and lifecycle rules. Prototype fixtures may remain explicitly fictional until this gate is met.

## 2. Database and contract readiness (§§5.1–5.2, 9.2, 10, 13.4)

- [x] Verify that `public.users.identity_subject` is unique, role/permission codes are unique, and assignment rows carry role, scope, validity, status and version fields.
- [x] Verify `public.users.id` references `auth.users.id`, allowed user/assignment statuses and the five scope types against database constraints. The identity query now requires both `id` and `identity_subject` to equal the verified Auth subject. The current read routes intentionally grant nothing from `campus` scope.
- [x] Inspect indexes and constraints for duplicate or overlapping active role assignments. No unique constraint or index prevents overlapping assignments beyond the row primary key.
- [ ] Decide and enforce duplicate/overlap validation in the approved grant contract before enabling writes.
- [ ] Define valid role/scope combinations, scope-ID referential checks, inactive/expired scope handling and region inheritance in one backend policy component. A user-supplied scope ID must never create access.
- [x] Inspect the current API database role: the live read-only check found `BYPASSRLS=true` and `rolsuper=false`. The current read routes apply explicit SQL filters; RLS cannot be counted as a second barrier with this connection.
- [ ] Replace the bypass-capable API connection with a least-privilege application role, then audit its RLS policies and table grants before enabling broader reads or writes.
- [ ] Define the exact request/response and reason/version contract for the PRD-listed `GET /users`, `POST /users/{id}/role-assignments` and `PATCH /users/{id}/role-assignments/{assignmentId}`. No extra public identity endpoints are assumed.
- [ ] Require `If-Match` or equivalent version preconditions for assignment edits, transaction-safe duplicate/overlap checks and idempotency where retry could create a second grant.
- [ ] Persist the assignment change and protected audit/outbox evidence atomically; record actor, target, old/new scope/status, reason, effective time and correlation ID without storing tokens or passwords.
- [ ] Define an approved provisioning mechanism for the **initial** administrator or policy owner before in-product grants exist. Keep service credentials out of the browser and repository; do not create an undocumented permanent superuser.

**Contract gate:** approved payload examples, invariants, denial behaviour, audit fields and migration impact are documented before enabling grant or revoke writes.

## 3. Implement and verify live identity (§§9.1–9.2, 13.1)

- [x] Create one authorised Supabase Auth account through the approved project administration flow. The confirmed test account was found without copying access or refresh tokens into files or chat.
- [x] Create the matching active `public.users` row with both `id = auth.users.id` and `identity_subject = auth.users.id`; verify uniqueness and status. Signing in does not auto-create this row.
- [x] Add only the approved test-only DEMO viewer role, two read permissions and one 30-day institution assignment, with policy-version and audit evidence. Broader official grants remain subject to the unsigned policy decision sheet.
- [x] Sign in through the live frontend and receive 200 from `/me`, the institution list and the application list with the provisioned test account.
- [ ] Confirm `/me/permissions` and the exact browser-visible identity, assignments and row counts; then exercise negative requests with the real token.
- [ ] Verify the first institution/application lists and details against **at least two** distinct scopes so both permitted and denied reads are observable. Empty lists alone do not prove scope enforcement.
- [ ] Verify expired token, bad signature, anonymous token and unprovisioned/disabled application user failures; do not expose records or token details in error responses.
- [ ] Verify that disabling a user or revoking/expiring an assignment removes effective access on the next backend request, even if the browser still holds an otherwise valid token.
- [ ] Verify switching between a user's approved assignments refreshes displayed scope and does not retain data from the previous scope.

**Read gate:** real-token browser/API evidence shows positive and negative access, prompt revocation, and no cross-scope leakage. Keep the existing six read routes as the first live slice; broader data routes follow their PRD modules.

## 4. Extend permissions with each PRD module (§§3, 7–9, 13)

- [ ] **Institutions/applications:** enforce authorised profile creation/edits, draft submission, case assignment, deficiency return, workflow transition, decision and closure. Require configured workflow guards in addition to permission.
- [ ] **Documents/OCR:** scope metadata and individual file access separately; restrict upload, check review, version history and downloads. OCR findings never grant verification authority.
- [ ] **EVC:** only the authorised officer selects/replaces experts; an expert sees only assigned visit material; scheduling confirmation rechecks committee and availability authority.
- [ ] **Meeting records:** restrict source inputs and transcripts, draft editing, review and final approval; approved history remains available only to authorised viewers.
- [ ] **Compliance/renewal:** separate evidence submission from verification, condition closure and reopening; restrict each action by role and record scope.
- [ ] **Notifications/reports/audit/admin:** authorise recipients, retries, report runs and actual downloads, audit inspection, configuration publication, integrations and job controls independently.
- [ ] Revalidate authorisation when a background worker performs a consequential action or delivers a scoped artifact; service identities must have narrowly approved capabilities.

**Module gate:** every new route has positive, wrong-role, wrong-scope, disabled-user, expired-assignment and stale/retry cases before the frontend action is labelled live.

## 5. Test matrix and acceptance evidence (§§17.1–17.5, 20)

| Scenario | Expected result | Check |
| --- | --- | --- |
| No token / malformed or expired token | 401; no data | [ ] |
| Valid Supabase token without `public.users` mapping | 403; no automatic grant | [ ] |
| Disabled application user or expired/revoked assignment | No effective access on next request | [ ] |
| Institution A user requests institution B or its files | No disclosure; 404 for hidden detail | [ ] |
| Direct region versus descendant region | Follows the approved hierarchy rule only | [ ] |
| Scrutiny officer requests unassigned case | Denied unless separately authorised | [ ] |
| EVC expert requests a different committee's material | Denied | [ ] |
| Auditor attempts workflow mutation | Denied; read/export only if explicitly granted | [ ] |
| System administrator attempts statutory approval | Denied unless separately, explicitly authorised | [ ] |
| Duplicate/overlapping grant or stale grant edit | Rejected without duplicate effect; 409/412 as contracted | [ ] |
| Grant/revoke, file download and decision actions | Correct protected audit event, no sensitive token/payload | [ ] |
| Role/scope switch or permission change during an open browser session | No stale records or actions remain accessible | [ ] |

- [ ] Add backend integration tests using real database policy rows in an isolated test context; preserve ordinary project records.
- [ ] Add browser tests for sign-in, allowed/denied navigation, scope switch, session expiry and recovery.
- [ ] Retain a redacted approval record, test results and traceable audit evidence for the PRD §20 demonstration. Do not publish credentials or personal data in the repository.

## Immediate handoff and decisions

1. **Policy owner:** provide the approved role/action/scope matrix, hierarchy decision, grant authority and stronger-authentication rule.
2. **Identity administrator:** the controlled test user and scoped DEMO read assignment are provisioned; browser sign-in reached the protected read APIs. Help verify revocation without sharing credentials.
3. **Backend teammate:** implement the broader approved provisioning/grant contract after policy sign-off and least-privilege database access; keep [access_policy.md](backend/docs/access_policy.md) aligned with the approved version.
4. **Frontend teammate:** exercise the live sign-in and read shell with that user; reveal additional actions only after their backend routes and denial tests exist.

Do not mark this P0 task complete until the **read gate** passes with a real authorised subject and the **contract gate** is approved for future grant/revoke operations.
