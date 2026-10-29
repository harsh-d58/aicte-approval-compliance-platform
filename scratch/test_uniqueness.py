import psycopg, re
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_WRITE_URL') or env.get('DATABASE_URL')

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, official_name, institution_code FROM public.institutions")
        rows = cur.fetchall()
        print(f"Total institutions: {len(rows)}")
        cleaned_names = set()
        duplicates = []
        for id_, name, code in rows:
            clean = re.sub(r"^DEMO\s+", "", name, flags=re.IGNORECASE)
            clean = re.sub(r"\s+\d{3,}$", "", clean)
            if clean in cleaned_names:
                duplicates.append((name, clean))
            cleaned_names.add(clean)
        print(f"Unique cleaned names: {len(cleaned_names)}, Duplicates: {len(duplicates)}")
        if duplicates:
            print("Sample duplicates:", duplicates[:5])

