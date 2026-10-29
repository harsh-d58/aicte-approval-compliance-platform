-- Additive CP01/03/04 history; apply through the controlled migration runner.
ALTER TABLE public.workflow_definitions ADD COLUMN IF NOT EXISTS effective_from date;
ALTER TABLE public.workflow_definitions ADD COLUMN IF NOT EXISTS effective_until date;
ALTER TABLE public.workflow_stages ADD COLUMN IF NOT EXISTS owner_role_code text;
ALTER TABLE public.institution_profile_attributes ADD COLUMN IF NOT EXISTS source_document_version_id uuid REFERENCES public.document_versions(id);

CREATE TABLE IF NOT EXISTS public.deficiency_item_responses (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 deficiency_item_id uuid NOT NULL REFERENCES public.deficiency_items(id),
 submission_id uuid NOT NULL REFERENCES public.application_submissions(id),
 narrative text NOT NULL CHECK (length(trim(narrative))>=3),
 document_version_id uuid REFERENCES public.document_versions(id),
 submitted_by uuid NOT NULL REFERENCES public.users(id),
 submitted_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(deficiency_item_id,submission_id)
);
ALTER TABLE public.deficiency_item_responses ENABLE ROW LEVEL SECURITY;
GRANT SELECT,INSERT ON public.deficiency_item_responses TO aicte_api_writer;
GRANT SELECT ON public.deficiency_item_responses TO aicte_api_reader;
DROP POLICY IF EXISTS writer_deficiency_responses ON public.deficiency_item_responses;
DROP POLICY IF EXISTS reader_deficiency_responses ON public.deficiency_item_responses;
CREATE POLICY writer_deficiency_responses ON public.deficiency_item_responses FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);
CREATE POLICY reader_deficiency_responses ON public.deficiency_item_responses FOR SELECT TO aicte_api_reader USING (EXISTS(SELECT 1 FROM public.deficiency_items i JOIN public.deficiency_notices n ON n.id=i.deficiency_notice_id JOIN public.applications a ON a.id=n.application_id WHERE i.id=deficiency_item_id AND api_private.can_read('application.read',a.institution_id,a.id)));
CREATE UNIQUE INDEX IF NOT EXISTS application_submission_number_unique ON public.application_submissions(application_id,submission_number);
