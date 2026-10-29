import psycopg
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_URL')

with open('backend/migrations/030_access_workflow_history.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

with psycopg.connect(url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        print("\nSuccessfully applied 030_access_workflow_history.sql to database!")
