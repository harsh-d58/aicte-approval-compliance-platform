-- Additive only. Apply with the migration role before deploying worker/API.
-- Existing historical attempts/audit rows are intentionally left untouched.
ALTER TABLE public.outbox_events ADD COLUMN dead_lettered_at timestamptz;
ALTER TABLE public.compliance_conditions ADD COLUMN overdue_detected_at timestamptz;
ALTER TABLE public.notifications DROP CONSTRAINT IF EXISTS notifications_status_check;
ALTER TABLE public.notifications ADD CONSTRAINT notifications_status_check CHECK
 (status IN ('queued','sent','failed','read','cancelled','blocked','accepted','delivered','dead_letter'));

CREATE TABLE public.notification_delivery_jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 notification_id uuid NOT NULL REFERENCES public.notifications(id) ON DELETE RESTRICT,
 channel text NOT NULL CHECK (channel IN ('email','sms','in_app')),
 status text NOT NULL DEFAULT 'queued' CHECK
  (status IN ('queued','sending','retry','blocked','accepted','delivered','failed','unknown','dead_letter')),
 attempt_count integer NOT NULL DEFAULT 0 CHECK(attempt_count BETWEEN 0 AND 8),
 available_at timestamptz NOT NULL DEFAULT now(),
 claim_token uuid, claimed_until timestamptz,
 provider_reference text, last_error text,
 accepted_at timestamptz, delivered_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(notification_id,channel),
 CHECK ((claim_token IS NULL) = (claimed_until IS NULL))
);
CREATE INDEX notification_jobs_due ON public.notification_delivery_jobs(available_at,id)
 WHERE status IN ('queued','retry','sending');
CREATE TABLE public.notification_delivery_receipts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 provider_event_id text NOT NULL UNIQUE CHECK(char_length(provider_event_id) BETWEEN 1 AND 160),
 job_id uuid NOT NULL REFERENCES public.notification_delivery_jobs(id) ON DELETE RESTRICT,
 outcome text NOT NULL CHECK(outcome IN ('delivered','failed')),
 received_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.notification_attempts ADD COLUMN delivery_job_id uuid REFERENCES public.notification_delivery_jobs(id);
ALTER TABLE public.notification_attempts ADD COLUMN provider_status text;
ALTER TABLE public.notification_delivery_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_delivery_receipts ENABLE ROW LEVEL SECURITY;
GRANT SELECT,INSERT,UPDATE ON public.notification_delivery_jobs TO aicte_api_writer;
GRANT SELECT,INSERT ON public.notification_delivery_receipts TO aicte_api_writer;
GRANT SELECT ON public.notification_delivery_jobs,public.notification_delivery_receipts TO aicte_api_reader;
CREATE POLICY notification_jobs_writer ON public.notification_delivery_jobs TO aicte_api_writer USING(true) WITH CHECK(true);
CREATE POLICY notification_receipts_writer ON public.notification_delivery_receipts TO aicte_api_writer USING(true) WITH CHECK(true);
CREATE POLICY notification_jobs_reader ON public.notification_delivery_jobs FOR SELECT TO aicte_api_reader
 USING(EXISTS(SELECT 1 FROM public.notifications n WHERE n.id=notification_id));
CREATE POLICY notification_receipts_reader ON public.notification_delivery_receipts FOR SELECT TO aicte_api_reader
 USING(EXISTS(SELECT 1 FROM public.notification_delivery_jobs j WHERE j.id=job_id));
-- Prevent scanner races without deleting/reclassifying pre-existing duplicates.
-- Transaction advisory locks in the scanner serialize document decisions. A
-- partial unique index can be added only after owners reconcile historical rows.
