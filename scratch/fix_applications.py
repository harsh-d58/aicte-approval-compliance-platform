with open("backend/app/applications.py", "r", encoding="utf-8") as f:
    text = f.read()

target = 'if not {role_name(r) for r in caller_roles}.intersection({"REGIONAL", "CENTRAL", owner_role}):'
replacement = 'if not {role_name(r) for r in caller_roles}.intersection({"REGIONAL", "CENTRAL", "SCRUTINY", owner_role}):'

if target in text:
    text = text.replace(target, replacement, 1)
    with open("backend/app/applications.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("SUCCESS: Updated applications.py")
else:
    print("FAILED: Target not found")

