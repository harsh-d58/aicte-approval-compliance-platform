import psycopg
from psycopg.rows import dict_row
from dotenv import dotenv_values
from datetime import datetime, timezone
import secrets

env = dotenv_values('.env')
write_url = env.get('DATABASE_WRITE_URL')
subject = "141ddc58-1483-5bf5-adf3-308953de2da3"

institution_id = "9cf0f959-2e6d-598b-8f4c-46fbf40894da"
campus_id = "c3dae2b0-c5ce-5eaa-82f5-8360bc1ba508"
workflow_definition_id = "385c30ee-381e-5639-a204-1de123c3a8f0"
application_type_id = "8af01a22-53fb-56f2-b9cb-084aaa7a265e"

with psycopg.connect(write_url, autocommit=True) as conn:
    with conn.transaction():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT set_config('aicte.subject_id', %s, true)", (subject,))
            
            # Step 1
            cur.execute("SELECT id FROM public.institutions WHERE id = %s", (institution_id,))
            inst_res = cur.fetchone()
            print("Step 1 (Institutions):", inst_res)
            
            # Step 2
            cur.execute("SELECT id FROM public.application_types WHERE id = %s AND status='active'", (application_type_id,))
            app_type_res = cur.fetchone()
            print("Step 2 (Application Type):", app_type_res)
            
            # Step 3
            cur.execute(
                "SELECT id FROM public.workflow_definitions WHERE id = %s AND application_type_id = %s AND status='published' AND (effective_from IS NULL OR effective_from<=CURRENT_DATE) AND (effective_until IS NULL OR effective_until>=CURRENT_DATE)",
                (workflow_definition_id, application_type_id),
            )
            wf_res = cur.fetchone()
            print("Step 3 (Workflow):", wf_res)
            
            # Step 4: Campus
            cur.execute("SELECT id FROM public.institution_campuses WHERE id=%s AND institution_id=%s", (campus_id, institution_id))
            campus_res = cur.fetchone()
            print("Step 4 (Campus):", campus_res)

