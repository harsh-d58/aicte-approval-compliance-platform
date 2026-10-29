import requests

base_url = "http://127.0.0.1:8000/api/v1"

# 1. Sign in as Ananya Rao (user-institution)
resp = requests.post(f"{base_url}/prototype/session", json={"persona_id": "user-institution"})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Get snapshot
snap = requests.get(f"{base_url}/portal/snapshot", headers=headers).json()
print("Snapshot user:", snap["users"][0]["displayName"])
inst = snap["institutions"][0]
print("Institution:", inst["name"], inst["code"], inst["id"])
campuses = inst["campuses"]
print("Campus:", campuses[0]["name"], campuses[0]["id"])

# 3. Get workflows
workflows = requests.get(f"{base_url}/workflows", headers=headers).json()["data"]
print("Published workflows count:", len(workflows))
for w in workflows:
    print(f" - {w['name']} (ID: {w['id']}, status: {w['status']})")

# 4. Create an Extension of Approval draft application
ext_wf = next(w for w in workflows if "Extension of approval" in w["name"])
payload = {
    "institution_id": inst["id"],
    "campus_id": campuses[0]["id"],
    "workflow_definition_id": ext_wf["id"],
    "application_type_id": ext_wf["application_type_id"],
    "reason": "Initial application draft creation via portal form",
}

create_resp = requests.post(f"{base_url}/applications", headers=headers, json=payload)
print("Create draft response:", create_resp.status_code, create_resp.json())
assert create_resp.status_code == 201
app_data = create_resp.json()
print(f"SUCCESS: Created draft application {app_data['application_number']} with ID {app_data['id']}")

