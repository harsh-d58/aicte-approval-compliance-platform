# Supabase Auth and scoped read policy — prototype contract

Supabase Auth verifies the person's identity. The application database remains authoritative for regulatory roles, permissions and scope. Supabase's JWT `role` claim must be `authenticated`, but it never grants an application role by itself.

## Auth configuration

1. Put the HTTPS project base URL in `SUPABASE_URL` in the ignored project root `.env`. The configured URL was checked against the project's public JWKS and exposes one ES256 signing key.
2. The backend derives issuer `<SUPABASE_URL>/auth/v1` and JWKS `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. It accepts Supabase Auth access tokens signed with ES256 or RS256 and checks signature, issuer, `authenticated` audience, expiry, issue time, user UUID, session UUID, `authenticated` role and non-anonymous status. HS256 tokens are rejected; this project has an asymmetric key, so no JWT signing secret is needed.
3. Provision an authorised user in `public.users` with both `id` and `identity_subject` equal to the Supabase Auth user's `sub`/`auth.users.id`. The backend requires both fields to match the verified subject. It does not auto-create application users from login tokens. Disabled, absent or mislinked application users are denied. One confirmed Supabase test account and matching application user are now provisioned under the approved test-only read policy.
4. The default frontend now has a live sign-in/read shell that sends the Supabase access token as `Authorization: Bearer <token>` to the API. The fictional demo is an explicit separate mode; browser-selected demo roles never grant live access.

See the [Supabase JWT verification guide](https://supabase.com/docs/guides/auth/jwts) and [JWT claims reference](https://supabase.com/docs/guides/auth/jwt-fields) for the provider contract. Supabase documents that legacy HS256 verification should call the Auth server instead of trusting a client-exposed shared secret; this backend deliberately requires the project's asymmetric signing key.

## Read permissions proposed for the first routes

These are internal permission codes for the new read endpoints; they are **not approved statutory role grants**. An authorised policy owner must assign them to roles in `public.role_permissions` and create valid `public.user_role_assignments` before records become visible.

| Permission code | Routes | Accepted scope from an active assignment |
| --- | --- | --- |
| `institution.read` | `GET /api/v1/institutions`, `GET /api/v1/institutions/{id}` | `global` with null ID; exact `institution` ID; direct `region` ID |
| `application.read` | `GET /api/v1/applications`, `GET /api/v1/applications/{id}` | `global` with null ID; exact `institution`, direct `region`, or exact `application` ID |

An assignment must have status `active`, `valid_from` no later than now, and `valid_until` later than now (or null). The application user must also have status `active`. These lowercase values match the database check constraints; `valid_from` is required by the database. Record filtering happens in SQL through `EXISTS` checks on the current application user ID, assignment, role permission, and scope. The listed region match covers the institution's direct `region_id`; descendant-region expansion is pending an approved hierarchy rule. The assignment table also permits `campus`, but these first read routes do not grant access from that scope. There is no `evc` assignment scope; future visit access requires an approved committee-membership rule. Unknown and out-of-scope detail IDs both return 404.

Cursor pagination uses an encoded UUID position with `limit` 1–100. A cursor affects ordering only and cannot grant visibility. One test-only institution viewer now has the two read permissions scoped to `DEMO-INST-0001`; database verification shows one institution and six applications, with other details denied. [Synthetic business records](mock_dataset.md) and the grant are not official AICTE access. No mutation permission was granted.

The role/action/scope approval template is [access_policy_decisions.md](access_policy_decisions.md). It does not itself authorise grants.
