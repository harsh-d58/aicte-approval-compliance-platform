"""Read-only, sanitized schema inspection for CP01/03/04."""
from pathlib import Path
from dotenv import dotenv_values
import psycopg

tables = ('roles','permissions','role_permissions','user_role_assignments','institution_profile_attributes','workflow_definitions','workflow_stages','workflow_transitions','aph_rule_versions','aph_rule_sets','application_types','application_submissions','deficiency_items','document_requirements','document_types','notification_rules','escalation_rules')
with psycopg.connect(dotenv_values(Path(__file__).resolve().parents[1]/'.env')['DATABASE_URL']) as conn:
    conn.read_only = True
    with conn.cursor() as cur:
        cur.execute("SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name=ANY(%s) ORDER BY table_name,ordinal_position",(list(tables),))
        for row in cur.fetchall(): print(*row)
        cur.execute("SELECT conrelid::regclass,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid::regclass::text=ANY(%s) AND contype='c'",(list(tables),))
        for row in cur.fetchall(): print(*row)
