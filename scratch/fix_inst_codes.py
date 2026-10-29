import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_WRITE_URL') or env.get('DATABASE_URL')

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("UPDATE public.institutions SET institution_code = REPLACE(institution_code, 'INST-INST-', 'INST-') WHERE institution_code LIKE 'INST-INST-%'")
        conn.commit()
        print("Updated institution codes:", cur.rowcount)

