import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_WRITE_URL') or env.get('DATABASE_URL')

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT i.id, i.official_name, r.name as region, c.city, c.campus_name
            FROM public.institutions i
            LEFT JOIN public.regions r ON r.id = i.region_id
            LEFT JOIN public.institution_campuses c ON c.institution_id = i.id AND c.is_primary = true
            LIMIT 10
        """)
        for row in cur.fetchall():
            print(row)

