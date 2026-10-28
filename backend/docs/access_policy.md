# Keycloak and scoped read policy — prototype contract

Keycloak authenticates the person. The database remains authoritative for application roles, permissions and scope. A Keycloak role claim or a UI-selected role never grants access by itself.

## Keycloak configuration needed

1. Configure a Keycloak realm and an API audience/client ID. Add the realm's exact discovery `issuer` to `IDENTITY_ISSUER_URL`, and the API audience value to `IDENTITY_AUDIENCE` in ignored `backend/.env`.
2. Configure the frontend client for Authorization Code with PKCE and ensure its access tokens contain the API audience. The backend accepts signed RS256 access tokens with valid `iss`, `aud`, `sub` and `exp` claims. It obtains signing keys from the realm's OIDC discovery document and JWKS.
3. Use HTTPS in shared environments. For local development only, `APP_ENV=development` permits a loopback issuer such as `http://localhost:8080/realms/aicte`; its JWKS must use the same origin. No Keycloak server or client credentials are bundled in this repository.
4. Provision an application user in `public.users` with `identity_subject` equal to Keycloak `sub`. The backend does not auto-create users from tokens. Disabled or absent users are denied.

## Read permissions proposed for the first routes

These are internal permission codes for the new read endpoints; they are **not approved statutory role grants**. An authorised policy owner must assign them to roles in `public.role_permissions` and create valid `public.user_role_assignments` before records become visible.

| Permission code | Routes | Accepted scope from an active assignment |
| --- | --- | --- |
| `institution.read` | `GET /api/v1/institutions`, `GET /api/v1/institutions/{id}` | `GLOBAL` with null ID; exact `INSTITUTION` ID; direct `REGION` ID |
| `application.read` | `GET /api/v1/applications`, `GET /api/v1/applications/{id}` | `GLOBAL` with null ID; exact `INSTITUTION`, direct `REGION`, or exact `APPLICATION` ID |

An assignment must have status `ACTIVE`, `valid_from` no later than now, and `valid_until` later than now (or null). Record filtering happens in SQL through `EXISTS` checks on the current application's user ID, assignment, role permission, and scope. The listed region match covers the institution's direct `region_id`; descendant-region expansion is pending an approved hierarchy rule. `EVC` scope does not grant full institution/application access through these routes. Unknown and out-of-scope detail IDs both return 404.

Cursor pagination uses an encoded UUID position with `limit` 1–100. A cursor affects ordering only and cannot grant visibility. The database currently has no user, role, permission or assignment records, so all business reads remain closed. No seed records or privileged accounts were inserted.
