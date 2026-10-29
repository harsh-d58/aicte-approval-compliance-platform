-- PRD §§8.2, 10.1: durable outbox and API idempotency records.
-- Run once, in one migration transaction, using an authorised migration role.
-- This file is intentionally not executed by application startup.
-- Runtime grants and RLS policies must be installed for a least-privilege role
-- before any business write route is enabled.

CREATE TABLE public.outbox_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type text NOT NULL CHECK (char_length(event_type) BETWEEN 1 AND 128),
    entity_type text NOT NULL CHECK (char_length(entity_type) BETWEEN 1 AND 128),
    entity_id uuid NOT NULL,
    entity_version integer CHECK (entity_version IS NULL OR entity_version > 0),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
    correlation_id uuid,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    available_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    claim_token uuid,
    claimed_until timestamptz,
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    processed_at timestamptz,
    last_error text,
    CONSTRAINT outbox_claim_pair CHECK ((claim_token IS NULL) = (claimed_until IS NULL))
);

CREATE INDEX outbox_events_due_idx
    ON public.outbox_events (available_at, created_at, id)
    WHERE processed_at IS NULL;

CREATE INDEX outbox_events_entity_idx
    ON public.outbox_events (entity_type, entity_id, created_at);

CREATE TABLE public.api_idempotency_records (
    actor_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    operation text NOT NULL CHECK (char_length(operation) BETWEEN 1 AND 128),
    key_hash text NOT NULL CHECK (key_hash ~ '^[0-9a-f]{64}$'),
    request_hash text NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    http_status smallint NOT NULL CHECK (http_status BETWEEN 200 AND 599),
    response_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (actor_id, operation, key_hash),
    CONSTRAINT api_idempotency_expiry CHECK (expires_at > created_at)
);

CREATE INDEX api_idempotency_expiry_idx
    ON public.api_idempotency_records (expires_at);

REVOKE ALL ON public.outbox_events FROM PUBLIC;
REVOKE ALL ON public.api_idempotency_records FROM PUBLIC;
ALTER TABLE public.outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_idempotency_records ENABLE ROW LEVEL SECURITY;
