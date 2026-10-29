# Update applications.py
with open('backend/app/applications.py', 'r', encoding='utf-8') as f:
    app_c = f.read()

target = """                # 3. Get destination stage info
                cur.execute(
                    "SELECT id, stage_code, stage_type, default_sla_days,owner_role_code FROM public.workflow_stages WHERE id = %s AND workflow_definition_id=%s",
                    (payload.to_stage_id, app["workflow_definition_id"]),
                )
                target_stage = cur.fetchone()
                if not target_stage:
                    raise HTTPException(status_code=400)
                if transition["requires_authorisation"] and target_stage.get("owner_role_code"):
                    # Advancing into a stage requires the responsible statutory
                    # reviewer, never technical administration alone.
                    if not {role_name(r) for r in caller_roles}.intersection({"REGIONAL", "CENTRAL", role_name(target_stage["owner_role_code"])}):
                        raise HTTPException(403)"""

replacement = """                # 3. Get destination stage info
                cur.execute(
                    "SELECT id, stage_code, stage_type, default_sla_days FROM public.workflow_stages WHERE id = %s AND workflow_definition_id=%s",
                    (payload.to_stage_id, app["workflow_definition_id"]),
                )
                target_stage = cur.fetchone()
                if not target_stage:
                    raise HTTPException(status_code=400)
                stage_role_map = {
                    "INTAKE": "INSTITUTION", "SCRUTINY": "SCRUTINY", "DEFICIENCY": "INSTITUTION",
                    "EVC": "EVC_COORDINATOR", "COMPLIANCE": "COMPLIANCE", "DECISION": "REGIONAL"
                }
                owner_role = stage_role_map.get((target_stage.get("stage_type") or "").upper(), "REGIONAL")
                if transition["requires_authorisation"] and owner_role:
                    if not {role_name(r) for r in caller_roles}.intersection({"REGIONAL", "CENTRAL", owner_role}):
                        raise HTTPException(403)"""

if target in app_c:
    app_c = app_c.replace(target, replacement)
    with open('backend/app/applications.py', 'w', encoding='utf-8') as f:
        f.write(app_c)
    print("Updated applications.py line 623 (LF)")
elif target.replace('\n', '\r\n') in app_c:
    app_c = app_c.replace(target.replace('\n', '\r\n'), replacement.replace('\n', '\r\n'))
    with open('backend/app/applications.py', 'w', encoding='utf-8') as f:
        f.write(app_c)
    print("Updated applications.py line 623 (CRLF)")
else:
    print("Target not found in applications.py")

# Update main.py for traceback printing
with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    main_c = f.read()

target_main = """        try:
            response = await call_next(request)
        except Exception:
            response = _error(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")"""

replacement_main = """        try:
            response = await call_next(request)
        except Exception:
            import traceback
            traceback.print_exc()
            response = _error(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")"""

if target_main in main_c:
    main_c = main_c.replace(target_main, replacement_main)
    with open('backend/app/main.py', 'w', encoding='utf-8') as f:
        f.write(main_c)
    print("Updated main.py traceback (LF)")
elif target_main.replace('\n', '\r\n') in main_c:
    main_c = main_c.replace(target_main.replace('\n', '\r\n'), replacement_main.replace('\n', '\r\n'))
    with open('backend/app/main.py', 'w', encoding='utf-8') as f:
        f.write(main_c)
    print("Updated main.py traceback (CRLF)")
else:
    print("target_main not found in main.py")
