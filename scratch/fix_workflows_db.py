import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
conn = psycopg.connect(env['DATABASE_WRITE_URL'])

with conn.cursor() as cur:
    # 1. Clean up application_types
    cur.execute("SELECT id, code, name FROM public.application_types")
    app_types = cur.fetchall()
    print("Before Application Types:", app_types)
    for at_id, code, name in app_types:
        new_name = name.replace("DEMO — ", "").replace("DEMO  ", "").replace("DEMO ", "").replace("ONLY — ", "").strip()
        new_code = code.replace("DEMO-", "")
        if new_name != name or new_code != code:
            cur.execute("UPDATE public.application_types SET name = %s, code = %s WHERE id = %s", (new_name, new_code, at_id))
            print(f"Updated app_type {code} -> {new_code}, {name} -> {new_name}")

    # 2. Clean up workflow_definitions and mark published
    cur.execute("SELECT id, name, status, application_type_id FROM public.workflow_definitions")
    wfs = cur.fetchall()
    print("\nBefore Workflows:", wfs)
    for wf_id, name, status, at_id in wfs:
        new_name = name.replace("DEMO — ", "").replace("DEMO  ", "").replace("DEMO ", "").replace("ONLY — ", "").replace("ONLY  ", "").replace("ONLY ", "").strip()
        cur.execute("UPDATE public.workflow_definitions SET name = %s, status = 'published' WHERE id = %s", (new_name, wf_id))
        print(f"Updated workflow {name} -> {new_name} (status=published)")

    conn.commit()
    print("\nCommitted updates to Supabase PostgreSQL.")

