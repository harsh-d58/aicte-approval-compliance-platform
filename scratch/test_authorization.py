import psycopg
from psycopg.rows import dict_row
from dotenv import dotenv_values
from uuid import UUID

env = dotenv_values('.env')
write_url = env.get('DATABASE_WRITE_URL')
subject = "141ddc58-1483-5bf5-adf3-308953de2da3"

with psycopg.connect(write_url) as conn:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT a.*,r.role_code FROM user_role_assignments a JOIN roles r ON r.id=a.role_id JOIN users u ON u.id=a.user_id WHERE u.id=%s AND u.identity_subject=%s AND u.status='active' AND a.status='active' AND (a.valid_from IS NULL OR a.valid_from<=now()) AND (a.valid_until IS NULL OR a.valid_until>now())", (UUID(subject), subject))
        assignments = cur.fetchall()
        print("Assignments for Ananya Rao:", assignments)
        
        all_demo = all(a["role_code"].startswith("DEMO_") for a in assignments)
        print("all_demo roles?", all_demo)
        
        inst_id = "9cf0f959-2e6d-598b-8f4c-46fbf40894da"
        sql = "SELECT id AS institution_id, region_id, NULL::uuid AS application_id, institution_code, created_by FROM institutions WHERE id=%s"
        cur.execute(sql, (inst_id,))
        row = cur.fetchone()
        print("Institution row:", row)
        
        starts_with_demo = str(row["institution_code"]).startswith("DEMO-")
        print("institution_code starts with DEMO-?", starts_with_demo)
        
        if all_demo and not starts_with_demo:
            print("FAILED CONDITION TRIGGERED! Checking created_by:", row["created_by"])
            cur.execute("SELECT 1 FROM user_role_assignments a JOIN roles r ON r.id=a.role_id WHERE a.user_id=%s AND r.role_code LIKE 'DEMO_%%'", (row["created_by"],))
            res = cur.fetchone()
            print("created_by query result:", res)
            if not res:
                print(">>> THIS RAISES HTTPException(404)! <<<")

