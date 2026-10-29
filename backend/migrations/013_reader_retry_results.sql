-- Replay cache remains actor-private; a retry cannot inspect another actor.
GRANT SELECT ON public.api_idempotency_records TO aicte_api_reader;
DROP POLICY IF EXISTS reader_own_retry_results ON public.api_idempotency_records;
CREATE POLICY reader_own_retry_results ON public.api_idempotency_records
 FOR SELECT TO aicte_api_reader USING(actor_id=api_private.subject_uuid());
