CREATE TABLE IF NOT EXISTS public.configuration_revisions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 family_id uuid NOT NULL,
 category text NOT NULL CHECK(category IN ('APH','DOCUMENT_TYPE','DOCUMENT_REQUIREMENT','COMMITTEE','TEMPLATE','RETENTION','NOTIFICATION','ESCALATION','SETTINGS')),
 name text NOT NULL,
 version integer NOT NULL CHECK(version>0),
 status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','superseded')),
 values jsonb NOT NULL,
 effective_from date,
 effective_until date,
 operational_id uuid,
 created_by uuid NOT NULL REFERENCES public.users(id),
 created_at timestamptz NOT NULL DEFAULT now(),
 approved_by uuid REFERENCES public.users(id),
 approved_at timestamptz,
 UNIQUE(family_id,version),
 CHECK(effective_until IS NULL OR effective_until>=effective_from)
);
ALTER TABLE public.configuration_revisions ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON public.configuration_revisions TO aicte_api_reader;
GRANT SELECT,INSERT,UPDATE ON public.configuration_revisions TO aicte_api_writer;
CREATE POLICY configuration_reader ON public.configuration_revisions FOR SELECT TO aicte_api_reader USING(true);
CREATE POLICY configuration_writer ON public.configuration_revisions FOR ALL TO aicte_api_writer USING(true) WITH CHECK(true);
