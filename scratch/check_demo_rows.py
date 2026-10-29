import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_WRITE_URL') or env.get('DATABASE_URL')

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        for table, col in [
            ("institutions", "official_name"),
            ("institutions", "institution_code"),
            ("applications", "application_number"),
            ("institution_campuses", "campus_name"),
            ("compliance_conditions", "condition_code"),
            ("compliance_conditions", "description"),
            ("deficiency_notices", "notice_number"),
            ("document_types", "document_type_code"),
            ("workflow_definitions", "name"),
            ("workflow_stages", "stage_name"),
            ("workflow_stages", "stage_code"),
            ("roles", "role_code"),
            ("roles", "role_name"),
        ]:
            try:
                cur.execute(f"SELECT count(*) FROM public.{table} WHERE {col} ILIKE '%DEMO%'")
                cnt = cur.fetchone()[0]
                print(f"{table}.{col}: {cnt}")
            except Exception as e:
                print(f"{table}.{col}: ERROR {e}")
                conn.rollback()

