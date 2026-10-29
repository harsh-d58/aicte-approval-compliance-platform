import psycopg
from dotenv import dotenv_values

env = dotenv_values(".env")
conn = psycopg.connect(env["DATABASE_URL"])
cur = conn.cursor()

cur.execute("SELECT id, user_id, expertise, eligibility_status, availability_method FROM public.expert_profiles")
print("expert_profiles rows:")
for r in cur.fetchall():
    print(r)

cur.execute("SELECT id, display_name, email FROM public.users WHERE id IN (SELECT user_id FROM public.expert_profiles)")
print("\nexpert users:")
for r in cur.fetchall():
    print(r)
