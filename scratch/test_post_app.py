import requests
import json

base_url = "http://127.0.0.1:8000/api/v1"

# 1. Sign in as user-institution
resp = requests.post(f"{base_url}/prototype/session", json={"persona_id": "user-institution"})
print("Session response:", resp.status_code, resp.json())
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Get workflows
w_resp = requests.get(f"{base_url}/workflows", headers=headers)
print("Workflows response:", w_resp.status_code)
workflows = w_resp.json()["data"]
print("Available workflows count:", len(workflows))
live_wf = next((w for w in workflows if "Live prototype" in w["name"] or "ONLY" in w["name"]), workflows[0])
print("Selected workflow:", live_wf)

# 3. Get me / snapshot to get institution ID
snap_resp = requests.get(f"{base_url}/portal/snapshot", headers=headers)
snap = snap_resp.json()
inst = snap["institutions"][0]
print("Institution:", inst["id"], inst["name"])
campus = inst["campuses"][0]
print("Campus:", campus["id"], campus["name"])

# 4. Try POST /applications with the published live workflow (UUID 385c30ee-381e-5639-a204-1de123c3a8f0)
live_wf = next(w for w in workflows if w["id"] == "385c30ee-381e-5639-a204-1de123c3a8f0")
print("Using published workflow:", live_wf)

payload = {
    "institution_id": inst["id"],
    "campus_id": campus["id"],
    "workflow_definition_id": live_wf["id"],
    "application_type_id": live_wf["application_type_id"],
    "reason": "Test draft creation from script",
}
print("Posting payload:", json.dumps(payload, indent=2))
app_resp = requests.post(f"{base_url}/applications", headers=headers, json=payload)
print("App response status:", app_resp.status_code)
print("App response body:", app_resp.text)
