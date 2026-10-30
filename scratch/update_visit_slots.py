import sys
sys.path.insert(0, ".")
import psycopg
from fastapi.testclient import TestClient
from backend.app.main import app

# 1. Update required_by for c606758d-948f-54ef-bf9d-979e62ebf808
db_url = [l.split("=", 1)[1].strip() for l in open(".env") if l.startswith("DATABASE_URL=")][0]
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute("UPDATE evc_visits SET required_by = '2026-11-20 12:00:00+00:00' WHERE id = 'c606758d-948f-54ef-bf9d-979e62ebf808';")
        conn.commit()
print("Updated required_by for c606758d-948f-54ef-bf9d-979e62ebf808")

# 2. Call generate_slot_recommendations via TestClient
client = TestClient(app)
resp = client.post("/api/v1/prototype/session", json={"persona_id": "user-regional"})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

for vid in ["c606758d-948f-54ef-bf9d-979e62ebf808", "25800af3-48bf-59b9-b8f7-0ecbb619d2a9"]:
    rec_resp = client.post(f"/api/v1/evc-visits/{vid}/slot-recommendations", headers=headers, json={"search_horizon_days": 30, "visit_duration_hours": 8.0})
    print(f"Visit {vid} recommendations status: {rec_resp.status_code}")
    print(f"Result: {rec_resp.json()}")

# 3. Print all slot_recommendations now in DB
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT evc_visit_id, start_at, end_at, rank, feasibility_status FROM slot_recommendations;")
        print("Slots in DB:")
        for r in cur.fetchall():
            print(r)
