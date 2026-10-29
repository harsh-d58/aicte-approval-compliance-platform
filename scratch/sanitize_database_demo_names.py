import psycopg, re
from dotenv import dotenv_values

env = dotenv_values('.env')
url = env.get('DATABASE_WRITE_URL') or env.get('DATABASE_URL')

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        # 1. Institutions
        cur.execute("""
            SELECT i.id, i.official_name, c.address->>'city' as city, c.address->>'state' as state
            FROM public.institutions i
            LEFT JOIN public.institution_campuses c ON c.institution_id = i.id AND c.is_primary = true
            ORDER BY i.official_name
        """)
        seen = {}
        inst_updates = []
        for id_, name, city, state in cur.fetchall():
            clean = re.sub(r"^DEMO\s+", "", name, flags=re.IGNORECASE)
            clean = re.sub(r"\s+\d{3,}$", "", clean).strip()
            if clean not in seen:
                seen[clean] = 1
                final_name = clean
            else:
                seen[clean] += 1
                loc = city or state or f"Campus {seen[clean]}"
                final_name = f"{clean}, {loc}"
            inst_updates.append((final_name, id_))
        
        cur.executemany("UPDATE public.institutions SET official_name = %s WHERE id = %s", inst_updates)
        print(f"Updated {len(inst_updates)} institution official_names.")

        # Update institution codes: DEMO-INST-0001 -> INST-0001
        cur.execute("UPDATE public.institutions SET institution_code = REGEXP_REPLACE(institution_code, '^DEMO-', 'INST-') WHERE institution_code LIKE 'DEMO-%'")
        print(f"Updated institution codes: {cur.rowcount} rows")

        # 2. Campuses: Remove 'DEMO ' prefix
        cur.execute("UPDATE public.institution_campuses SET campus_name = REGEXP_REPLACE(campus_name, '^DEMO\\s+', '', 'i') WHERE campus_name ILIKE 'DEMO %'")
        print(f"Updated campus_names: {cur.rowcount} rows")

        # 3. Applications: Replace DEMO-LIVE- with AICTE-2026- and DEMO-APP- with AICTE-APP-
        cur.execute("UPDATE public.applications SET application_number = REPLACE(application_number, 'DEMO-LIVE-', 'AICTE-2026-') WHERE application_number LIKE 'DEMO-LIVE-%'")
        print(f"Updated live applications: {cur.rowcount} rows")
        cur.execute("UPDATE public.applications SET application_number = REPLACE(application_number, 'DEMO-APP-', 'AICTE-APP-') WHERE application_number LIKE 'DEMO-APP-%'")
        print(f"Updated other applications: {cur.rowcount} rows")

        # 4. Compliance conditions: Remove 'DEMO ONLY – ' and DEMO- from code
        cur.execute("""
            UPDATE public.compliance_conditions 
            SET description = 'Submit a dated facilities compliance update',
                condition_code = REPLACE(condition_code, 'DEMO-COND-', 'COND-2026-')
            WHERE condition_code LIKE 'DEMO-%' OR description ILIKE '%DEMO%'
        """)
        print(f"Updated compliance conditions: {cur.rowcount} rows")

        # 5. Deficiency notices: DEMO-DEF- -> DEF-2026-
        cur.execute("UPDATE public.deficiency_notices SET notice_number = REPLACE(notice_number, 'DEMO-DEF-', 'DEF-2026-') WHERE notice_number LIKE 'DEMO-%'")
        print(f"Updated deficiency notices: {cur.rowcount} rows")

        # 6. Document types
        cur.execute("UPDATE public.document_types SET document_type_code = REPLACE(document_type_code, 'DEMO-', ''), name = REGEXP_REPLACE(name, '^DEMO\\s+', '', 'i') WHERE document_type_code LIKE 'DEMO-%' OR name ILIKE 'DEMO %'")
        print(f"Updated document types: {cur.rowcount} rows")

        # 7. Workflow definitions & stages
        cur.execute("UPDATE public.workflow_definitions SET name = REGEXP_REPLACE(name, '^DEMO\\s+', '', 'i') WHERE name ILIKE 'DEMO %'")
        print(f"Updated workflow definitions: {cur.rowcount} rows")
        cur.execute("UPDATE public.workflow_stages SET stage_name = REGEXP_REPLACE(stage_name, '^DEMO\\s+', '', 'i'), stage_code = REPLACE(stage_code, 'DEMO-', '') WHERE stage_code LIKE 'DEMO-%' OR stage_name ILIKE 'DEMO %'")
        print(f"Updated workflow stages: {cur.rowcount} rows")

        conn.commit()
        print("MIGRATION COMMITTED SUCCESSFULLY!")

