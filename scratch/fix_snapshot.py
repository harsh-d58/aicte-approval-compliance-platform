with open('backend/app/portal_snapshot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'assigned_apps = {a["application_id"] for a in tables.get("assignments", []) if a.get("assigned_user_id") == subject and a.get("status") == "active"}' in line:
        new_lines.append('        assigned_apps = {a["application_id"] for a in tables.get("assignments", []) if a.get("assigned_user_id") == subject}\n')
    else:
        new_lines.append(line)

with open('backend/app/portal_snapshot.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Updated portal_snapshot.py successfully')
