import psycopg, re
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_WRITE_URL') or env.get('DATABASE_URL')

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        # Check sample institutions
        cur.execute("SELECT id, official_name, institution_code FROM public.institutions LIMIT 5")
        for row in cur.fetchall():
            clean_name = re.sub(r"^DEMO\s+", "", row[1], flags=re.IGNORECASE)
            clean_name = re.sub(r"\s+\d{3,}$", "", clean_name)
            print(f"'{row[1]}' -> '{clean_name}'")

        # Check sample applications
        cur.execute("SELECT id, application_number FROM public.applications LIMIT 5")
        for row in cur.fetchall():
            clean_num = row[1].replace("DEMO-LIVE-", "AICTE-2026-").replace("DEMO-", "APP-")
            clean_num = re.sub(r"-001$", "", clean_num)
            print(f"'{row[1]}' -> '{clean_num}'")

        # Check sample conditions
        cur.execute("SELECT id, condition_code, description FROM public.compliance_conditions LIMIT 5")
        for row in cur.fetchall():
            clean_desc = re.sub(r"^DEMO\s+ONLY\s+[–\-]\s*", "", row[2], flags=re.IGNORECASE)
            clean_code = row[1].replace("DEMO-", "")
            print(f"'{row[1]}': '{row[2]}' -> '{clean_code}': '{clean_desc}'")

