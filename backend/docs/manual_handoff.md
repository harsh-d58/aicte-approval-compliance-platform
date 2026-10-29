# Manual decisions and setup for the next live build gate

Source: [full-scale implementation plan](../../full_scale_implementation_plan.md), [identity plan](../../identity_access_plan.md), and PRD §§3, 8.2, 13.1, 21. Updated 29 October 2026. These are the items the project team must supply or approve; the repository cannot infer official authority or create a safe runtime database account on its own.

## Required before the first business write route

1. **Policy owner:** the project owner approved the narrow [test-only read policy](prototype_access_proposal.md), and one DEMO viewer grant has been provisioned. For broader modules, complete and sign [access_policy_decisions.md](access_policy_decisions.md), including grant/revoke authority, region inheritance, institution representation, assigned-case and EVC membership access, conflicts of duty, stronger authentication and first-administrator provisioning. The test approval does not authorise official or write grants.
2. **Database owner:** create a separate least-privilege API role with no `BYPASSRLS` or superuser flag; review policies and table grants for each live read/write. The current configured connection has `BYPASSRLS=true`. Set the new runtime `DATABASE_URL` only in the ignored root `.env` or an approved secret manager. Keep the migration/owner credential separate. Verify the runtime flags with `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user;` and test in-scope/out-of-scope queries.
3. **Database/migration owner:** review installed [001_outbox_idempotency.sql](../migrations/001_outbox_idempotency.sql), [002_audit_append_only.sql](../migrations/002_audit_append_only.sql) and the [transaction contract](transaction_foundation.md). The two infrastructure tables and audit triggers are now present in the connected prototype database, but least-privilege runtime grants/RLS policies, backup/change review and an isolated integration environment still need owner verification before business writes.
4. **Identity administrator:** one confirmed Supabase Auth test account has been linked to `public.users.id` and `identity_subject` with a 30-day, institution-scoped DEMO read assignment and audit evidence. Browser sign-in reached `/me`, institutions and applications with 200 responses. Verify the exact visible scope, denied reads and revocation with the real token. Do not paste passwords, tokens, service keys or the database URL in chat or Git.

## Required as their PRD modules are reached

- **Policy/operations owners:** approve APH workflow versions, stage guards, deadlines, application categories and statutory sign-off rules before official case routing.
- **EVC owners:** approve committee composition, availability method, scheduling timezone/deadline and permitted calendar/meeting providers.
- **Document/security owners:** approve document types/expiry rules, private storage and malware-scanning service, transcript retention and authorised file access.
- **Communications/report owners:** approve notification channels/templates and the definitions, audiences and filters of all eight report categories.
- **Integration/hosting owners:** approve existing AICTE APIs, authoritative field ownership, data sharing, production identity/hosting and service-level targets.
- **Governance owner:** decide whether an optional permissioned-ledger demonstration or production rollout is justified. The append-only audit trail is required either way.

The narrow read-policy and account setup are complete. Positive browser-token reads passed; denied reads and revocation remain, as does the least-privilege database role and broader approved grant contract. These gates precede the first protected business write route; the six existing GET routes remain the only live business API slice.
