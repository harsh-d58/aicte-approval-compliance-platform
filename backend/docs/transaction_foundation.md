# Transaction foundation contract

Source: [PRD v1.0](<../../Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md>) §§8.2, 9.1, 10.1–10.3, 13.4. The additive [migration](../migrations/001_outbox_idempotency.sql) was installed in the connected database on 29 October 2026. It adds two infrastructure tables; it does not change the 65 PRD business entities or grant any user access.

The [transaction helper](../app/transactions.py) now opens an explicit TLS transaction and rejects superuser/`BYPASSRLS` roles before yielding a connection. It also computes stable SHA-256 hashes for bounded client retry keys and canonical JSON requests. No API route invokes this helper yet; role/scope rechecks, audit/outbox writes and idempotent replay still need implementation.

The [outbox primitives](../app/outbox.py) now insert an event in the caller's transaction, lease due events with `FOR UPDATE SKIP LOCKED`, release a failed claim for retry, and acknowledge only the current claim token. A [database smoke check](../verify_outbox.py) exercised insert/claim/retry/ack and rolled back its test event. No worker or business route calls these functions yet.

The [idempotency helper](../app/idempotency.py) supports completed-result lookup, changed-request conflict detection and same-transaction result insertion. Expired rows keep their keys reserved rather than being mistaken for new requests; cleanup/retention must be approved before allowing key reuse. A rolled-back [atomic action smoke check](../verify_atomic_action.py) now exercises insertion and replay with the approved DEMO test identity. A two-session concurrency check stalled on this shared database and was stopped without a committed row; that race remains for an isolated integration database.

The [version guard](../app/concurrency.py) locks and checks an expected positive row version for applications, institutions and documents before a module-specific mutation. It can advance the version in the same transaction. The API error envelope now recognises 409 conflicts and 412 stale preconditions. The synthetic atomic check verified stale-version rejection and rollback of a DEMO application version update together with audit, outbox and idempotency rows. No business route invokes these helpers yet.

## One committed business action

For each sensitive mutation, a single PostgreSQL transaction must:

1. Resolve the verified application user and recheck the active role, exact record scope and applicable workflow guard inside the write transaction.
2. Lock or version-check the affected row. Reject stale versions with 412, conflicting operations with 409, and invalid transitions without changing state.
3. Write the business state and immutable history, a protected `audit_events` row, and any required `outbox_events` row in that same transaction.
4. If the operation is retryable, write its completed idempotency result in the same transaction before commit.
5. Commit once. A failed guard, audit insert, outbox insert or idempotency insert rolls back the entire action. Do not call external providers inside the transaction.

The existing `audit_events.event_hash` is required. [Migration 002](../migrations/002_audit_append_only.sql) installed append-only UPDATE/DELETE/TRUNCATE triggers. A rolled-back smoke event proved UPDATE and DELETE are rejected by those triggers; TRUNCATE was rejected by the existing audit-anchor foreign key before its trigger ran. [Per-event canonical hashing](../app/audit.py) now includes ID, actor, action, entity, UTC event time, correlation, reason, metadata and optional previous hash. Its insert/read verification passed a rolled-back database check. Protected grants, backup integrity, chain/anchor policy and business-action integration remain open. The outbox does not replace the audit trail.

## Outbox lifecycle

- A business route inserts one event with an internal `event_type`, entity/version reference, correlation ID and minimal JSON payload. The payload must not contain tokens, signed file URLs, full transcripts or unnecessary personal data.
- The worker claims due, unprocessed events using `FOR UPDATE SKIP LOCKED`, a unique `claim_token` and a bounded `claimed_until` lease. It records attempts and a sanitised error. Expired leases can be reclaimed after interruption.
- `processed_at` means the permitted downstream effect was durably recorded, not merely accepted by a transport. A crash can cause redelivery, so every consumer deduplicates by `outbox_events.id`. Retry/backoff limits and operational alerts come from approved worker policy.
- A failed worker does not rewrite or roll back the already committed business action. Notification records remain separate from delivery attempts as PRD §8.2 requires.

## Idempotency lifecycle

- For each retry-sensitive API operation, identify `(actor_id, operation, key_hash)`. Hash the client key before storage; do not store raw keys. Hash the canonical request semantics separately as `request_hash`.
- On a retry with the same key and request hash, return the stored status and JSON result while rechecking current access to any referenced record. The same key with a different request hash is a conflict; it must not rerun the action.
- Insert the *completed* result in the business transaction. A concurrent duplicate may attempt the same work, but the unique primary key makes one transaction roll back; retry it as a read of the committed result. No external side effect occurs before commit; outbox consumers are independently idempotent.
- `expires_at` and cleanup retention must be approved per operation. Store no access token, refresh token or temporary download URL in `response_json`. Protect table reads and backups because results may still contain scoped data.

## Migration and runtime gate

- [x] Draft additive outbox/idempotency schema with due-work and expiry indexes, unique idempotency key, restricted public grants and RLS enabled.
- [x] Add and unit-test the guarded write transaction and deterministic idempotency fingerprint helpers.
- [ ] Review schema names, retention, payload minimisation and indexes with the backend/database owner.
- [ ] Replace the current `BYPASSRLS` API connection with a least-privilege runtime role; add and test exact table grants/RLS policies for API and worker responsibilities.
- [x] Install the numbered additive migration in one transaction and confirm both tables have RLS enabled; the existing configured database credential was used for this prototype install.
- [ ] Review the installed table grants and add/test exact RLS policies for least-privilege API and worker roles.
- [x] Verify outbox insert, expired-lease recovery, retry and acknowledgement SQL against the database with a rolled-back smoke event.
- [x] Verify a versioned DEMO record update, audit event, outbox event and completed idempotency result are present together inside one transaction and disappear together after a forced rollback. The smoke script retains no data.
- [x] Verify that an expired idempotency key is rejected rather than treated as a fresh request; unit tests cover stale version and 409/412 error codes.
- [x] Install audit append-only triggers and verify UPDATE/DELETE rejection with a rolled-back smoke event; TRUNCATE is also blocked by the audit-anchor relationship.
- [ ] Integrate transaction/retry code with a real authorised business route and worker, then verify concurrent duplicates, lease recovery and duplicate delivery in an isolated integration database. The shared-database two-session race check stalled and was not counted as passing.
- [x] Define and test one-event canonical hashing and read-back verification against the database.
- [ ] Review chain/anchor policy, table grants, backup protection and business-action audit integration before sensitive mutations go live.

Do not infer that creating these tables makes workflow writes safe. The first write endpoint is gated on the transaction, permission, audit and retry tests above.
