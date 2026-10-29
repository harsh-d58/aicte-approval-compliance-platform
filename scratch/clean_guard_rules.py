import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
conn = psycopg.connect(env['DATABASE_WRITE_URL'])
with conn.cursor() as cur:
    cur.execute("""
        UPDATE public.workflow_transitions 
        SET guard_rule = '{}'::jsonb 
        WHERE guard_rule = '{"approved": false, "demo_only": true}'::jsonb
    """)
    conn.commit()
    print("Cleaned mock guard_rules in workflow_transitions.")
