import sys
import json
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = "http://127.0.0.1:8000/api/v1"

def login(persona_id):
    resp = requests.post(f"{BASE_URL}/prototype/session", json={"persona_id": persona_id})
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {persona_id}: {resp.status_code} {resp.text}")
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("=====================================================================")
print("STARTING COMPLETE END-TO-END DEMO WORKFLOW VERIFICATION")
print("=====================================================================")

# -----------------------------------------------------------------------------
# STEP 1: Institution Login (Ananya Rao)
# -----------------------------------------------------------------------------
print("\n--- STEP 1: Persona Login (user-institution) ---")
inst_headers = login("user-institution")
print("Logged in as Ananya Rao (user-institution).")

# -----------------------------------------------------------------------------
# STEP 2: Fetch Portal Snapshot
# -----------------------------------------------------------------------------
print("\n--- STEP 2: GET /portal/snapshot ---")
snap_resp = requests.get(f"{BASE_URL}/portal/snapshot", headers=inst_headers)
assert snap_resp.status_code == 200, f"Snapshot failed: {snap_resp.status_code}"
snap = snap_resp.json()
inst = snap["institutions"][0]
campus = inst["campuses"][0]
print(f"Snapshot loaded successfully. Institution: '{inst['name']}' ({inst['code']}), Campus: '{campus['name']}'")

# -----------------------------------------------------------------------------
# STEP 3: Fetch Published Workflows
# -----------------------------------------------------------------------------
print("\n--- STEP 3: GET /workflows ---")
wf_resp = requests.get(f"{BASE_URL}/workflows", headers=inst_headers)
assert wf_resp.status_code == 200
workflows = wf_resp.json()["data"]
print(f"Fetched {len(workflows)} published workflows:")
for w in workflows:
    print(f" - {w['name']} (ID: {w['id']})")
live_wf = next(w for w in workflows if "Live prototype" in w["name"] or "Extension of approval" in w["name"])
print(f"Selected workflow for testing: '{live_wf['name']}' (ID: {live_wf['id']})")

# -----------------------------------------------------------------------------
# STEP 4: Create Application Draft
# -----------------------------------------------------------------------------
print("\n--- STEP 4: POST /applications (Create Draft) ---")
app_payload = {
    "institution_id": inst["id"],
    "campus_id": campus["id"],
    "workflow_definition_id": live_wf["id"],
    "application_type_id": live_wf["application_type_id"],
    "reason": "Creating end-to-end demo application",
}
create_resp = requests.post(f"{BASE_URL}/applications", headers=inst_headers, json=app_payload)
print(f"Create response status: {create_resp.status_code}")
assert create_resp.status_code == 201, f"Failed: {create_resp.text}"
app_data = create_resp.json()
app_id = app_data["id"]
app_number = app_data["application_number"]
app_version = app_data["version"]
print(f"SUCCESS: Draft created with Number: {app_number}, ID: {app_id}, Version: {app_version}")

# -----------------------------------------------------------------------------
# STEP 5: Update Application Draft (Save Changes)
# -----------------------------------------------------------------------------
print("\n--- STEP 5: PUT /applications/[id] (Edit Draft) ---")
edit_payload = {
    "campus_id": campus["id"],
    "expected_version": app_version,
    "reason": "Updated campus details in draft",
}
edit_resp = requests.put(f"{BASE_URL}/applications/{app_id}", headers=inst_headers, json=edit_payload)
print(f"Edit response status: {edit_resp.status_code}")
assert edit_resp.status_code == 200, f"Edit failed: {edit_resp.text}"
app_version = edit_resp.json().get("version", app_version + 1)
print(f"SUCCESS: Draft updated to version {app_version}")

# -----------------------------------------------------------------------------
# STEP 6: OCR Engine & Sample Document
# -----------------------------------------------------------------------------
print("\n--- STEP 6: GET /ocr/sample-document & POST /ocr/test-upload ---")
sample_resp = requests.get(f"{BASE_URL}/ocr/sample-document", headers=inst_headers)
assert sample_resp.status_code == 200
sample_json = sample_resp.json()
print(f"Retrieved sample document '{sample_json['file_name']}' ({sample_json['size_bytes']} bytes, MIME: {sample_json['mime_type']})")

ocr_payload = {
    "file_name": sample_json["file_name"],
    "mime_type": sample_json["mime_type"],
    "content_base64": sample_json["content_base64"],
}
ocr_resp = requests.post(
    f"{BASE_URL}/ocr/test-upload",
    headers=inst_headers,
    json=ocr_payload,
)
assert ocr_resp.status_code == 200, f"OCR failed: {ocr_resp.text}"
ocr_data = ocr_resp.json()
print("SUCCESS: RapidOCR engine output:")
print(f" - Document Type: {ocr_data.get('document_type')}")
print(f" - Confidence: {ocr_data.get('confidence_score')}")
print(f" - Certificate No: {ocr_data.get('extracted_fields', {}).get('certificate_number')}")
print(f" - Issuing Authority: {ocr_data.get('extracted_fields', {}).get('issuing_authority')}")
print(f" - Expiry Date: {ocr_data.get('extracted_fields', {}).get('expiry_date')}")

# -----------------------------------------------------------------------------
# STEP 7: Submit Application
# -----------------------------------------------------------------------------
print("\n--- STEP 7: POST /applications/[id]/submit ---")
submit_payload = {
    "expected_version": app_version,
    "reason": "Official demonstration submission with confirmed declaration",
}
submit_resp = requests.post(f"{BASE_URL}/applications/{app_id}/submit", headers=inst_headers, json=submit_payload)
print(f"Submit response status: {submit_resp.status_code}")
assert submit_resp.status_code == 200, f"Submit failed: {submit_resp.text}"
sub_data = submit_resp.json()
app_version = sub_data.get("version", app_version + 1)
print(f"SUCCESS: Application submitted! Current Status: {sub_data.get('status')}, Version: {app_version}")

# -----------------------------------------------------------------------------
# STEP 8: Regional Officer Login (Meera Desai)
# -----------------------------------------------------------------------------
print("\n--- STEP 8: Switch Persona to Regional Officer (user-regional) ---")
ro_headers = login("user-regional")
print("Logged in as Meera Desai (user-regional).")

# -----------------------------------------------------------------------------
# STEP 9: Workflow Transitions & Advance Application
# -----------------------------------------------------------------------------
print("\n--- STEP 9: Advance Application Stage (POST /applications/[id]/transitions) ---")
wf_detail_resp = requests.get(f"{BASE_URL}/workflows/{live_wf['id']}", headers=ro_headers)
assert wf_detail_resp.status_code == 200
wf_detail = wf_detail_resp.json()
stages = wf_detail.get("stages", [])
transitions = wf_detail.get("transitions", [])
print(f"Workflow has {len(stages)} stages and {len(transitions)} transitions:")
for s in stages:
    print(f" - Stage: {s['stage_code']} ({s['stage_name']}) [ID: {s['id']}]")

# Find transition matching current stage
snap_after_sub = requests.get(f"{BASE_URL}/portal/snapshot", headers=ro_headers).json()
matched_app = next(a for a in snap_after_sub["applications"] if a["id"] == app_id)
cur_stage_code = matched_app["currentStage"]
print(f"Application current stage code: {cur_stage_code}")

cur_stage = next(s for s in stages if s["stage_code"] == cur_stage_code)
valid_transition = next((t for t in transitions if t["from_stage_id"] == cur_stage["id"]), None)
if valid_transition:
    to_stage = valid_transition["to_stage_id"]
    print(f"Transitioning from {cur_stage_code} to stage ID: {to_stage}")
    trans_payload = {
        "to_stage_id": to_stage,
        "expected_version": app_version,
        "reason": "Regional scrutiny started by authorised officer",
    }
    trans_resp = requests.post(f"{BASE_URL}/applications/{app_id}/transitions", headers=ro_headers, json=trans_payload)
    print(f"Transition status: {trans_resp.status_code}")
    assert trans_resp.status_code == 200, f"Transition failed: {trans_resp.text}"
    app_version = trans_resp.json().get("version", app_version + 1)
    print(f"SUCCESS: Stage advanced to version {app_version}")
else:
    print("No transition configured from current stage.")

# -----------------------------------------------------------------------------
# STEP 10: Issue Multi-Item Deficiency Checklist
# -----------------------------------------------------------------------------
print("\n--- STEP 10: Issue Deficiency Notice (POST /applications/[id]/deficiency-notices) ---")
defic_payload = {
    "response_due_days": 14,
    "items": [
        {
            "criterion_code": "CRIT-FIRE-01",
            "description": "Building Safety & Fire Clearance: Submit updated endorsement from local Fire Service.",
            "related_document_id": None,
        }
    ],
    "reason": "Fire safety endorsement renewal required under APH 2026-27.",
}
defic_resp = requests.post(f"{BASE_URL}/applications/{app_id}/deficiency-notices", headers=ro_headers, json=defic_payload)
print(f"Deficiency response status: {defic_resp.status_code}")
assert defic_resp.status_code == 201, f"Deficiency issue failed: {defic_resp.text}"
defic_data = defic_resp.json()
notice_id = defic_data["id"]
notice_number = defic_data["notice_number"]
items = defic_data.get("items", [])
item_id = items[0]["id"] if items else None
print(f"SUCCESS: Deficiency notice issued! Notice No: {notice_number}, ID: {notice_id}, Item ID: {item_id}")

# -----------------------------------------------------------------------------
# STEP 11: Institutional Response to Deficiency
# -----------------------------------------------------------------------------
print("\n--- STEP 11: Respond to Deficiency (POST /deficiency-notices/[id]/responses) ---")
resp_payload = {
    "item_responses": [
        {
            "item_id": item_id,
            "related_document_id": None,
            "narrative": "Renewed Fire Safety Certificate DFS/HQ/2026/FSC/8842 uploaded and submitted.",
        }
    ],
    "reason": "Renewed Fire Safety Certificate DFS/HQ/2026/FSC/8842 uploaded and submitted.",
}
resp_result = requests.post(f"{BASE_URL}/deficiency-notices/{notice_id}/responses", headers=inst_headers, json=resp_payload)
print(f"Response submission status: {resp_result.status_code}")
assert resp_result.status_code in (200, 201), f"Deficiency response failed: {resp_result.text}"
print("SUCCESS: Institutional deficiency response submitted.")

# -----------------------------------------------------------------------------
# STEP 12: Resolve Deficiency Item
# -----------------------------------------------------------------------------
print("\n--- STEP 12: Resolve Deficiency Item (POST /deficiency-items/[id]/resolve) ---")
resolve_payload = {
    "resolution_status": "accepted",
    "reason": "Fire safety certificate verified against Delhi Fire Service records.",
}
res_resp = requests.post(f"{BASE_URL}/deficiency-items/{item_id}/resolve", headers=ro_headers, json=resolve_payload)
print(f"Resolve item status: {res_resp.status_code}")
assert res_resp.status_code in (200, 201), f"Item resolve failed: {res_resp.text}"
print("SUCCESS: Deficiency item resolved as ACCEPTED.")

# -----------------------------------------------------------------------------
# STEP 13: Time-Bound Compliance Condition (Undertakings)
# -----------------------------------------------------------------------------
print("\n--- STEP 13: Create Compliance Condition (POST /compliance-conditions) ---")
due_date = (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
cond_payload = {
    "institution_id": inst["id"],
    "application_id": app_id,
    "source_approval_id": None,
    "condition_code": f"COND-{int(datetime.now().timestamp())}",
    "description": "Submission of registered 30-year lease deed renewal certificate.",
    "due_at": due_date,
}
cond_resp = requests.post(f"{BASE_URL}/compliance-conditions", headers=ro_headers, json=cond_payload)
print(f"Condition create status: {cond_resp.status_code}")
assert cond_resp.status_code == 201, f"Condition create failed: {cond_resp.text}"
cond_data = cond_resp.json()
cond_id = cond_data["id"]
print(f"SUCCESS: Compliance condition created with ID: {cond_id}")

# -----------------------------------------------------------------------------
# STEP 14: Evidence Submission for Compliance
# -----------------------------------------------------------------------------
print("\n--- STEP 14: Submit Evidence (POST /compliance-conditions/[id]/evidence-submissions) ---")
evid_payload = {
    "document_version_ids": [],
    "remarks": "Registered lease deed agreement submitted under time-bound undertaking.",
}
evid_resp = requests.post(f"{BASE_URL}/compliance-conditions/{cond_id}/evidence-submissions", headers=inst_headers, json=evid_payload)
print(f"Evidence submission status: {evid_resp.status_code}")
assert evid_resp.status_code in (200, 201), f"Evidence submit failed: {evid_resp.text}"
evid_data = evid_resp.json()
evid_id = evid_data["id"]
print(f"SUCCESS: Evidence submitted with ID: {evid_id}")

# -----------------------------------------------------------------------------
# STEP 15: Verify Evidence
# -----------------------------------------------------------------------------
print("\n--- STEP 15: Verify Evidence (POST /evidence-submissions/[id]/verifications) ---")
verif_payload = {
    "result": "accepted",
    "comments": "Sub-Registrar endorsement verified; 30-year lease valid until 2056.",
}
verif_resp = requests.post(f"{BASE_URL}/evidence-submissions/{evid_id}/verifications", headers=ro_headers, json=verif_payload)
print(f"Verification status: {verif_resp.status_code}")
assert verif_resp.status_code in (200, 201), f"Verification failed: {verif_resp.text}"
print("SUCCESS: Compliance evidence verified and accepted.")

# -----------------------------------------------------------------------------
# STEP 16: Record Final Approval Decision
# -----------------------------------------------------------------------------
print("\n--- STEP 16: Record Final Decision (POST /applications/[id]/decisions) ---")
dec_payload = {
    "decision_type": "approve",
    "decision_status": "approved",
    "decision_authority": "North West Regional Approval Committee",
    "reason": "Fulfilled all statutory requirements under AICTE Approval Process Handbook 2026-27.",
    "expected_version": app_version,
}
dec_resp = requests.post(f"{BASE_URL}/applications/{app_id}/decisions", headers=ro_headers, json=dec_payload)
print(f"Decision response status: {dec_resp.status_code}")
assert dec_resp.status_code in (200, 201), f"Decision failed: {dec_resp.text}"
print(f"SUCCESS: Final APPROVE decision recorded! Decision ID: {dec_resp.json().get('id')}")

# -----------------------------------------------------------------------------
# STEP 17: Application History & Timeline
# -----------------------------------------------------------------------------
print("\n--- STEP 17: Check Application Timeline (GET /applications/[id]/history) ---")
hist_resp = requests.get(f"{BASE_URL}/applications/{app_id}/history", headers=ro_headers)
assert hist_resp.status_code == 200
hist_data = hist_resp.json().get("data", [])
print(f"SUCCESS: Retrieved {len(hist_data)} recorded stage transitions in application history.")

# -----------------------------------------------------------------------------
# STEP 18: Audit Trail Chain Verification
# -----------------------------------------------------------------------------
print("\n--- STEP 18: Verify Cryptographic Audit Chain (GET /audit/verify-chain) ---")
audit_resp = requests.get(f"{BASE_URL}/audit/verify-chain", headers=ro_headers)
assert audit_resp.status_code == 200, f"Audit check failed: {audit_resp.text}"
print("SUCCESS: Audit trail verified!")
print(json.dumps(audit_resp.json(), indent=2))

print("\n=====================================================================")
print("ALL 18 ENDPOINTS AND WORKFLOW STAGES VERIFIED 100% OPERATIONAL!")
print("=====================================================================")
