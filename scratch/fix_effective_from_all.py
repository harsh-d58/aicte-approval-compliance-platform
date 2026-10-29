# Fix applications.py line 404
with open('backend/app/applications.py', 'r', encoding='utf-8') as f:
    app_c = f.read()

target1 = """                cur.execute(
                    "SELECT id, stage_code, stage_name, default_sla_days FROM public.workflow_stages "
                    "WHERE workflow_definition_id = %s AND EXISTS (SELECT 1 FROM public.workflow_definitions w WHERE w.id=workflow_definition_id AND w.status='published' AND (w.effective_from IS NULL OR w.effective_from<=CURRENT_DATE) AND (w.effective_until IS NULL OR w.effective_until>=CURRENT_DATE)) ORDER BY stage_order ASC LIMIT 1",
                    (app["workflow_definition_id"],),
                )"""

replacement1 = """                cur.execute(
                    "SELECT id, stage_code, stage_name, default_sla_days FROM public.workflow_stages "
                    "WHERE workflow_definition_id = %s AND EXISTS (SELECT 1 FROM public.workflow_definitions w WHERE w.id=workflow_definition_id AND w.status='published') ORDER BY stage_order ASC LIMIT 1",
                    (app["workflow_definition_id"],),
                )"""

if target1 in app_c:
    app_c = app_c.replace(target1, replacement1)
    with open('backend/app/applications.py', 'w', encoding='utf-8') as f:
        f.write(app_c)
    print("Fixed line 404 in applications.py (LF)")
elif target1.replace('\n', '\r\n') in app_c:
    app_c = app_c.replace(target1.replace('\n', '\r\n'), replacement1.replace('\n', '\r\n'))
    with open('backend/app/applications.py', 'w', encoding='utf-8') as f:
        f.write(app_c)
    print("Fixed line 404 in applications.py (CRLF)")
else:
    print("target1 not found in applications.py")

# Fix portal_commands.py line 178
with open('backend/app/portal_commands.py', 'r', encoding='utf-8') as f:
    pc_c = f.read()

target2 = "cur.execute(\"SELECT application_type_id FROM public.workflow_definitions WHERE id=%s AND status='published' AND (effective_from IS NULL OR effective_from<=CURRENT_DATE) AND (effective_until IS NULL OR effective_until>=CURRENT_DATE)\", (workflow[\"id\"],))"
replacement2 = "cur.execute(\"SELECT application_type_id FROM public.workflow_definitions WHERE id=%s AND status='published'\", (workflow[\"id\"],))"

if target2 in pc_c:
    pc_c = pc_c.replace(target2, replacement2)
    with open('backend/app/portal_commands.py', 'w', encoding='utf-8') as f:
        f.write(pc_c)
    print("Fixed line 178 in portal_commands.py")
else:
    print("target2 not found in portal_commands.py")
