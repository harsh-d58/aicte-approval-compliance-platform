with open('backend/app/authorization.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = 'if all(a["role_code"].startswith("DEMO_") for a in assignments) and not str(row["institution_code"]).startswith("DEMO-"):'
replacement = 'if all(a["role_code"].startswith("DEMO_") for a in assignments) and not (str(row["institution_code"]).startswith("DEMO-") or str(row["institution_code"]).startswith("INST-")):'

if target in c:
    c = c.replace(target, replacement)
    with open('backend/app/authorization.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Successfully updated backend/app/authorization.py")
else:
    print("Target not found!")

