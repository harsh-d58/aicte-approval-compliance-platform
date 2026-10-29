import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
conn = psycopg.connect(env['DATABASE_URL'])
with conn.cursor() as cur:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='workflow_definitions'")
    for r in cur.fetchall():
        print(r)

