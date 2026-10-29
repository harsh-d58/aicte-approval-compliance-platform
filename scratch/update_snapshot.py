import re

with open("backend/app/portal_snapshot.py", "r", encoding="utf-8") as f:
    text = f.read()

# Replace all_institutions filter
old_all_inst = """    all_institutions = index([i for i in tables.get("institutions", [])
                              if not prototype or str(i.get("institution_code", "")).startswith("DEMO-")
                              or i.get("created_by") in prototype_subjects])"""
new_all_inst = """    all_institutions = index(tables.get("institutions", []))"""
if old_all_inst in text:
    text = text.replace(old_all_inst, new_all_inst)
    print("Replaced all_institutions")
else:
    print("old_all_inst not matched directly, trying regex")
    text = re.sub(r'all_institutions = index\(\[i for i in tables\.get\("institutions", \[\]\)\s+if not prototype.*?\n\s+or i\.get\("created_by"\) in prototype_subjects\]\)', 'all_institutions = index(tables.get("institutions", []))', text, flags=re.DOTALL)

# Add clean_text wrapping on institution fields
text = text.replace('"code": i.get("institution_code") or "", "name": i["official_name"]', '"code": clean_text(i.get("institution_code") or ""), "name": clean_text(i["official_name"])')
text = text.replace('"name": c["campus_name"]', '"name": clean_text(c["campus_name"])')

# Add clean_text on applications
text = text.replace('"number": a["application_number"]', '"number": clean_text(a["application_number"])')

# Add clean_text on conditions
text = text.replace('"code": c["condition_code"], "description": c["description"]', '"code": clean_text(c["condition_code"]), "description": clean_text(c["description"])')

# Add clean_text on deficiencies
text = text.replace('"number": str(n["notice_number"])', '"number": clean_text(str(n["notice_number"]))')

with open("backend/app/portal_snapshot.py", "w", encoding="utf-8") as f:
    f.write(text)

print("portal_snapshot.py updated successfully!")

