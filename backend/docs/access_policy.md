# Supabase Auth and scoped read policy — prototype contract

Supabase Auth verifies the person's identity. The application database remains authoritative for regulatory roles, permissions and scope. Supabase's JWT `role` claim must be `authenticated`, but it never grants an application role by itself.

## Auth configuration

1. Put the HTTPS project base URL in `SUPABASE_URL` in ignored `backend/.env`. This checkout's value was derived from the connected database project and checked against its public JWKS; the project currently exposes one ES256 signing key.
2. The backend derives issuer `<SUPABASE_URL>/auth/v1` and JWKS `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. It accepts Supabase Auth access tokens signed with ES256 or RS256 and checks signature, issuer, `authenticated` audience, expiry, issue time, user UUID, session UUID, `authenticated` role and non-anonymous status. HS256 tokens are rejected; this project has an asymmetric key, so no JWT signing secret is needed.
3. Provision an authorised user in `public.users` with `identity_subject` equal to the Supabase Auth user's `sub`/`auth.users.id`. The backend does not auto-create application users from login tokens. Disabled or absent application users are denied. The database currently has zero rows in both `auth.users` and `public.users`.
4. The frontend currently runs in demo mode. A live adapter must obtain the Supabase user's access token and send it as `Authorization: Bearer <token>` to the API; it must not treat browser-selected demo roles as grants.

See the [Supabase JWT verification guide](https://supabase.com/docs/guides/auth/jwts) and [JWT claims reference](https://supabase.com/docs/guides/auth/jwt-fields) for the provider contract. Supabase documents that legacy HS256 verification should call the Auth server instead of trusting a client-exposed shared secret; this backend deliberately requires the project's asymmetric signing key.

## Read permissions proposed for the first routes

These are internal permission codes for the new read endpoints; they are **not approved statutory role grants**. An authorised policy owner must assign them to roles in `public.role_permissions` and create valid `public.user_role_assignments` before records become visible.

| Permission code | Routes | Accepted scope from an active assignment |
| --- | --- | --- |
| `institution.read` | `GET /api/v1/institutions`, `GET /api/v1/institutions/{id}` | `GLOBAL` with null ID; exact `INSTITUTION` ID; direct `REGION` ID |
| `application.read` | `GET /api/v1/applications`, `GET /api/v1/applications/{id}` | `GLOBAL` with null ID; exact `INSTITUTION`, direct `REGION`, or exact `APPLICATION` ID |

An assignment must have status `ACTIVE`, `valid_from` no later than now, and `valid_until` later than now (or null). Record filtering happens in SQL through `EXISTS` checks on the current application user ID, assignment, role permission, and scope. The listed region match covers the institution's direct `region_id`; descendant-region expansion is pending an approved hierarchy rule. `EVC` scope does not grant full institution/application access through these routes. Unknown and out-of-scope detail IDs both return 404.

Cursor pagination uses an encoded UUID position with `limit` 1–100. A cursor affects ordering only and cannot grant visibility. The database currently has no application users, roles, permissions or assignments, so all business reads remain closed. No seed records or privileged accounts were inserted.
