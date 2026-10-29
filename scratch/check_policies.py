import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
conn = psycopg.connect(env['DATABASE_WRITE_URL'])
with conn.cursor() as cur:
    cur.execute("""
        SELECT polname, polcmd, polroles::regrole[], polpermissive, pg_get_expr(polqual, polrelid), pg_get_expr(polwithcheck, polrelid)
        FROM pg_policy
        WHERE polrelid = 'public.institutions'::regclass
    """)
    for r in cur.fetchall():
        print("POLICY:", r)
    
    # Also check current user
    cur.execute("SELECT current_user, session_user")
    print("CURRENT USERS:", cur.fetchall())
    
    # Also test the exact query under aicte_api_writer with aicte.subject_id set!
    subject = "141ddc58-1483-5bf5-adf3-308953de2da3"
    with conn.transaction():
        cur.execute("SELECT set_config('aicte.subject_id', %s, true)", (subject,))
        cur.execute("SELECT id FROM public.institutions WHERE id = %s", ('9cf0f959-2e6d-598b-8f4c-46fbf40894da',))
        print("Query result with subject:", cur.fetchone())
