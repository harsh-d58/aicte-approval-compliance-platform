import psycopg
from dotenv import dotenv_values
from backend.app.prototype import persona_subject

env = dotenv_values('.env')
url = env.get('DATABASE_WRITE_URL') or env.get('DATABASE_URL')
subject = persona_subject("user-institution")
print("Subject for Ananya Rao:", subject)

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        # Check user
        cur.execute("SELECT id, display_name FROM public.users WHERE id = %s", (subject,))
        print("User:", cur.fetchone())

        # Check user's assigned institution
        cur.execute("""
            SELECT a.scope_type, a.scope_id 
            FROM public.user_role_assignments a 
            WHERE a.user_id = %s AND a.status = 'active'
        """, (subject,))
        assignments = cur.fetchall()
        print("Assignments:", assignments)

        # Look up institution for that scope_id
        if assignments:
            inst_id = assignments[0][1]
            cur.execute("SELECT * FROM public.institutions WHERE id = %s", (inst_id,))
            inst_row = cur.fetchone()
            print("Assigned Institution:", inst_row)

        # What happens when we set aicte.subject_id?
        cur.execute("SELECT set_config('aicte.subject_id', %s, true)", (str(subject),))
        cur.execute("SELECT id, official_name FROM public.institutions")
        insts = cur.fetchall()
        print(f"Visible institutions under aicte.subject_id ({len(insts)}):", insts[:5])

        # Check campuses for the assigned institution
        cur.execute("SELECT * FROM public.institution_campuses WHERE institution_id = %s", (inst_id,))
        print("Campuses:", cur.fetchall())

        # Check application types
        cur.execute("SELECT id, code, name FROM public.application_types")
        types = cur.fetchall()
        print("Application types:", types)

        # Check workflows
        cur.execute("SELECT id, name, application_type_id, status FROM public.workflow_definitions")
        wfs = cur.fetchall()
        print("Workflows:", wfs)
