# Proposed test-only access policy for the first live read slice

**Status: approved for test-only use by the project owner in chat on 29 October 2026; version `DEMO-READ-V1`.** This is a small synthetic-data test policy, not an official AICTE role matrix. It covers only the six implemented read endpoints and the `DEMO-` records described in [mock_dataset.md](mock_dataset.md). It does not authorise application submission, decisions, uploads, reports, exports or administration. PRD basis: §§3.2–3.3, 9.2 and 13.1.

| Test role | Permission codes | Scope assignment | What it may see |
| --- | --- | --- | --- |
| `DEMO_INSTITUTION_VIEWER` | `institution.read`, `application.read` | Exact `institution` UUID for `DEMO-INST-0001` | That institution and its six DEMO applications |
| `DEMO_REGION_VIEWER` | `institution.read`, `application.read` | Direct `region` UUID for `DEMO-R01` | Institutions whose `region_id` is that UUID, and their applications; no descendant inheritance |
| `DEMO_APPLICATION_VIEWER` | `application.read` | Exact `application` UUID for `DEMO-APP-2026-000001` | That one application, without institution-profile read permission |

Only controlled Supabase Auth test accounts may receive these roles. Their `public.users.id` and `identity_subject` must both equal the verified Auth subject. Assignments use lowercase `active` status, have an explicit start and end time, and expire after **30 days** unless renewed by the test owner. No `global` grant is proposed. A browser-selected role cannot change backend access. Disabled users and revoked/expired assignments lose access on the next request.

## Acceptance checks after approval and provisioning

- [ ] Each test account sees its expected records through `/me`, `/me/permissions`, institution and application list/detail.
- [ ] An institution viewer cannot see a different institution or its applications; hidden detail returns 404.
- [ ] A region viewer sees only direct region matches; another region is excluded.
- [ ] An application viewer sees exactly one application and no institution profile.
- [ ] Disabling an account or revoking/expiring an assignment removes access on the next API request.
- [ ] No write, file, report, audit or administration action becomes available from these read-only codes.

**Approval record:** project owner approved the policy as written in this chat on 29 October 2026; version `DEMO-READ-V1`. One confirmed Supabase test account was provisioned as `DEMO_INSTITUTION_VIEWER` for `DEMO-INST-0001` with a 30-day assignment and a canonical-hash audit event. The other two test roles are approved definitions but have not been provisioned. The broader official policy remains open in [access_policy_decisions.md](access_policy_decisions.md).

Read-only database verification passed: exactly one institution and six applications are visible to the provisioned account, other institution/application details return 404, and the assignment audit hash verifies. Browser sign-in then reached `/me`, institutions and applications with 200 responses. Exact browser-visible counts, real-token denied details and revocation remain to be checked.
