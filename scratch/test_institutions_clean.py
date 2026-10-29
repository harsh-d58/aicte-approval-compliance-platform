import psycopg, re
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_WRITE_URL') or env.get('DATABASE_URL')

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT i.id, i.official_name, c.address->>'city' as city, c.address->>'state' as state
            FROM public.institutions i
            LEFT JOIN public.institution_campuses c ON c.institution_id = i.id AND c.is_primary = true
            ORDER BY i.official_name
        """)
        rows = cur.fetchall()
        seen = {}
        for id_, name, city, state in rows:
            clean = re.sub(r"^DEMO\s+", "", name, flags=re.IGNORECASE)
            clean = re.sub(r"\s+\d{3,}$", "", clean).strip()
            if clean not in seen:
                seen[clean] = 1
                final_name = clean
            else:
                seen[clean] += 1
                loc = city or state or f"Campus {seen[clean]}"
                final_name = f"{clean}, {loc}"
            print(f"{name}  --->  {final_name}")

