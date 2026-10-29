-- Persist honest scan evidence independently from human verification.
CREATE TABLE IF NOT EXISTS public.document_file_scans (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 document_version_id uuid NOT NULL REFERENCES public.document_versions(id),
 status text NOT NULL CHECK(status IN ('clean','infected','unavailable','error')),
 evidence jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.document_file_scans ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON public.document_file_scans TO aicte_api_reader;
GRANT SELECT,INSERT ON public.document_file_scans TO aicte_api_writer;
CREATE POLICY document_file_scan_reader ON public.document_file_scans FOR SELECT TO aicte_api_reader
 USING (EXISTS (SELECT 1 FROM public.document_versions v WHERE v.id=document_version_id));
CREATE POLICY document_file_scan_writer ON public.document_file_scans FOR ALL TO aicte_api_writer
 USING (EXISTS (SELECT 1 FROM public.document_versions v WHERE v.id=document_version_id))
 WITH CHECK (EXISTS (SELECT 1 FROM public.document_versions v WHERE v.id=document_version_id));
ALTER TABLE public.upload_sessions ADD COLUMN IF NOT EXISTS object_key text;
ALTER TABLE public.upload_sessions ADD COLUMN IF NOT EXISTS sha256_hash text;
ALTER TABLE public.upload_sessions ADD COLUMN IF NOT EXISTS size_bytes bigint;
ALTER TABLE public.upload_sessions ADD COLUMN IF NOT EXISTS finalized_version_id uuid REFERENCES public.document_versions(id);
-- New writes are immutable except a separate human verification assessment.
CREATE OR REPLACE FUNCTION public.enforce_document_version_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Historical document versions cannot be deleted'; END IF;
 IF (to_jsonb(NEW)-'verification_status') IS DISTINCT FROM (to_jsonb(OLD)-'verification_status')
 THEN RAISE EXCEPTION 'Historical document version bytes and metadata are immutable'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS immutable_document_version ON public.document_versions;
CREATE TRIGGER immutable_document_version BEFORE UPDATE OR DELETE ON public.document_versions
 FOR EACH ROW EXECUTE FUNCTION public.enforce_document_version_immutable();
CREATE UNIQUE INDEX IF NOT EXISTS one_active_document_renewal
 ON public.document_renewal_cases(document_id) WHERE status NOT IN ('closed','cancelled','verified','completed','rejected');
