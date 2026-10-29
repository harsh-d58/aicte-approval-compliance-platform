# Prototype integration audit — 29 October 2026

Policy: planning=deep; context_depth=dependency; verification_depth=full;
delegation=conditional investigator/impact auditor. Reasons: shared data source,
more than five page consumers, live database writes, inconsistent phase claims.

Scope: preserve Supabase authentication and existing ten demo persona logins;
connect existing portal and dashboards to the seeded PostgreSQL dataset; persist
business actions through the backend; expose errors rather than fixture fallbacks.
Existing uncommitted work belongs to the user and must be preserved.

Acceptance evidence to collect:
- Live dataset inventory and honest phase/PRD gap matrix.
- All ten personas retain their existing entry points and scoped navigation.
- Portal registers and analytics derive from the same live data, refresh after
  writes, and survive reload.
- Business actions enforce server-side authorization and concurrency.
- Backend tests, frontend scope tests, type/build checks, live integration proof.

Initial finding: DemoProvider calls fixture-only portalDataSource and applies
commands locally; LiveProvider/LivePortal are separate. Thus backend verification
scripts do not establish full portal integration. Brief completion claims are
unsupported until the portal adapter and user journeys are verified.
