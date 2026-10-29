import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_URL')

create_sql = """
CREATE TABLE IF NOT EXISTS public.deficiency_item_responses (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 deficiency_item_id uuid NOT NULL REFERENCES public.deficiency_items(id),
 submission_id uuid NOT NULL REFERENCES public.application_submissions(id),
 narrative text NOT NULL CHECK (length(trim(narrative))>=1),
 document_version_id uuid REFERENCES public.document_versions(id),
 submitted_by uuid NOT NULL REFERENCES public.users(id),
 submitted_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(deficiency_item_id,submission_id)
);
ALTER TABLE public.deficiency_item_responses ENABLE ROW LEVEL SECURITY;
GRANT SELECT,INSERT ON public.deficiency_item_responses TO aicte_api_writer;
GRANT SELECT ON public.deficiency_item_responses TO aicte_api_reader;
DROP POLICY IF EXISTS writer_deficiency_responses ON public.deficiency_item_responses;
CREATE POLICY writer_deficiency_responses ON public.deficiency_item_responses FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS reader_deficiency_responses ON public.deficiency_item_responses;
CREATE POLICY reader_deficiency_responses ON public.deficiency_item_responses FOR SELECT TO aicte_api_reader USING (true);
"""

with psycopg.connect(url, autocommit=True, connect_timeout=15) as conn:
    with conn.cursor() as cur:
        cur.execute(create_sql)
        print("Created deficiency_item_responses and set RLS + grants successfully!")
