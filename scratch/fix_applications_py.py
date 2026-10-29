with open('backend/app/applications.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = """                # 3. Verify workflow definition exists and matches type
                cur.execute(
                    "SELECT id FROM public.workflow_definitions WHERE id = %s AND application_type_id = %s AND status='published' AND (effective_from IS NULL OR effective_from<=CURRENT_DATE) AND (effective_until IS NULL OR effective_until>=CURRENT_DATE)",
                    (payload.workflow_definition_id, payload.application_type_id),
                )"""

replacement = """                # 3. Verify workflow definition exists and matches type
                cur.execute(
                    "SELECT id FROM public.workflow_definitions WHERE id = %s AND application_type_id = %s AND status='published'",
                    (payload.workflow_definition_id, payload.application_type_id),
                )"""

# Handle CRLF if needed
target_crlf = target.replace('\n', '\r\n')
replacement_crlf = replacement.replace('\n', '\r\n')

if target in c:
    c = c.replace(target, replacement)
    with open('backend/app/applications.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Successfully updated applications.py (LF)")
elif target_crlf in c:
    c = c.replace(target_crlf, replacement_crlf)
    with open('backend/app/applications.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Successfully updated applications.py (CRLF)")
else:
    print("Target not found!")

