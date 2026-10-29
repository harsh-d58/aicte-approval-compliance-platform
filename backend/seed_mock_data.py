"""Deterministic, synthetic PRD demo data. No Auth users, grants, or real files.

Preview: .venv/Scripts/python backend/seed_mock_data.py
Apply:   .venv/Scripts/python backend/seed_mock_data.py --apply
"""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from dotenv import dotenv_values
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
NAMESPACE = "sih-prd-synthetic-demo-v1"
ROWS = defaultdict(list)


def uid(kind: str, key: str | int):
    return uuid5(NAMESPACE_URL, f"{NAMESPACE}/{kind}/{key}")


def add(table: str, **fields):
    ROWS[table].append(fields)


def days_ago(number: int):
    return AT - timedelta(days=number)


LOCATIONS = [
    ("North", "Delhi", "Delhi"), ("North-West", "Jaipur", "Rajasthan"),
    ("West", "Pune", "Maharashtra"), ("West-Central", "Ahmedabad", "Gujarat"),
    ("South", "Bengaluru", "Karnataka"), ("South-East", "Chennai", "Tamil Nadu"),
    ("South-West", "Hyderabad", "Telangana"), ("East", "Kolkata", "West Bengal"),
    ("East-Central", "Bhubaneswar", "Odisha"), ("Central", "Bhopal", "Madhya Pradesh"),
    ("North-East", "Guwahati", "Assam"), ("North-Central", "Lucknow", "Uttar Pradesh"),
]
TYPES = [
    ("NEW_INSTITUTION", "New institution application"),
    ("EXTENSION", "Extension of approval"),
    ("INTAKE_CHANGE", "Proposed intake change"),
    ("NEW_PROGRAMME", "Proposed new programme"),
]
DOC_TYPES = [
    ("LAND_LEASE", "Land or lease evidence", True),
    ("BUILDING_PLAN", "Building plan", False),
    ("FIRE_SAFETY", "Fire safety certificate", True),
    ("AFFILIATION", "Affiliation evidence", True),
    ("FINANCIAL", "Financial statement", False),
]
STAGES = [
    ("INTAKE", "Intake", 7), ("SCRUTINY", "Document scrutiny", 21),
    ("DEFICIENCY", "Deficiency response", 30),
    ("EVC", "Expert visit", 45), ("DECISION", "Decision", 14),
]
REPORTS = [
    ("REGION_PERFORMANCE", "Region-wise performance"),
    ("APPLICATION_PENDENCY", "Application pendency"),
    ("EVC_STATUS", "EVC status"),
    ("UNDERTAKING_COMPLIANCE", "Undertaking compliance"),
    ("DOCUMENT_VALIDITY", "Document validity"),
    ("OVERDUE_ACTIONS", "Overdue actions"),
    ("NOTIFICATION_DELIVERY", "Notification delivery"),
    ("CASE_CLOSURE", "Case closure"),
]


def build_rows():
    for region_no, (label, _, _) in enumerate(LOCATIONS):
        add("regions", id=uid("region", region_no), code=f"DEMO-R{region_no+1:02d}",
            name=f"DEMO {label} Region", status="active")

    for type_no, (code, name) in enumerate(TYPES):
        type_id = uid("application_type", type_no)
        rules_id = uid("aph_rule_set", type_no)
        version_id = uid("aph_rule_version", type_no)
        workflow_id = uid("workflow", type_no)
        add("application_types", id=type_id, code=f"DEMO-{code}", name=f"DEMO — {name}",
            description="Synthetic category for interface and query testing; not an official application type.", status="active")
        add("aph_rule_sets", id=rules_id, rule_set_code=f"DEMO-APH-{type_no+1}",
            title=f"DEMO ONLY — sample rules for {name}",
            source_reference="SYNTHETIC DEMO; not an AICTE APH rule", status="draft")
        add("aph_rule_versions", id=version_id, rule_set_id=rules_id, version_number=1,
            content_reference=f"demo://sample-rules/{type_no+1}",
            checksum=sha256(f"demo-rule-{type_no}".encode()).hexdigest())
        add("workflow_definitions", id=workflow_id, name=f"DEMO ONLY — {name} flow",
            application_type_id=type_id, aph_rule_version_id=version_id,
            status="draft", version_number=1)
        for stage_no, (code, label, sla) in enumerate(STAGES):
            add("workflow_stages", id=uid("stage", f"{type_no}-{stage_no}"),
                workflow_definition_id=workflow_id, stage_code=f"DEMO-{code}",
                stage_name=label, stage_order=stage_no+1, stage_type=code.lower(),
                default_sla_days=sla)
        for stage_no in range(len(STAGES)-1):
            add("workflow_transitions", id=uid("transition", f"{type_no}-{stage_no}"),
                workflow_definition_id=workflow_id,
                from_stage_id=uid("stage", f"{type_no}-{stage_no}"),
                to_stage_id=uid("stage", f"{type_no}-{stage_no+1}"),
                transition_type="demo_forward",
                guard_rule=Jsonb({"demo_only": True, "approved": False}),
                requires_authorisation=True)

    for type_no, (code, name, expires) in enumerate(DOC_TYPES):
        add("document_types", id=uid("document_type", type_no), document_type_code=f"DEMO-{code}",
            name=f"DEMO — {name}", description="Synthetic metadata only; no file is stored.",
            supports_expiry=expires, metadata_schema=Jsonb({"demo_only": True}))

    status_cycle = ["draft", "submitted", "under_review", "under_review", "deficiency_returned",
                    "resubmitted", "approved", "closed", "rejected", "under_review"]
    for institution_no in range(180):
        region_no = institution_no % len(LOCATIONS)
        _, city, state = LOCATIONS[region_no]
        institution_id = uid("institution", institution_no)
        campus_id = uid("campus", institution_no)
        adjective = ["Cedar", "Riverbend", "Summit", "Oakridge", "Horizon", "Maple",
                     "Bluefield", "Silverlake", "Hillcrest", "Greenway"][institution_no % 10]
        discipline = ["Technology", "Management", "Engineering", "Applied Sciences"][institution_no % 4]
        add("institutions", id=institution_id,
            official_name=f"DEMO {adjective} Institute of {discipline} {institution_no+1:03d}",
            institution_code=f"DEMO-INST-{institution_no+1:04d}",
            institution_type=["private", "public", "trust", "university"][institution_no % 4],
            status="active" if institution_no % 13 else "pending",
            region_id=uid("region", region_no))
        add("institution_campuses", id=campus_id, institution_id=institution_id,
            campus_name=f"DEMO {city} Main Campus", region_id=uid("region", region_no),
            is_primary=True, address=Jsonb({"line1": f"{institution_no+10} Demo Campus Road",
                                            "city": city, "state": state, "postal_code": f"{500000+institution_no:06d}",
                                            "country": "India", "demo_only": True}))

        for local_no in range(6):
            app_no = institution_no * 6 + local_no
            application_id = uid("application", app_no)
            type_no = app_no % len(TYPES)
            status = status_cycle[app_no % len(status_cycle)]
            created = days_ago(20 + (app_no * 17) % 440)
            submitted = created + timedelta(days=3) if status != "draft" else None
            closed = submitted + timedelta(days=45 + app_no % 80) if status == "closed" else None
            if closed and closed > AT:
                closed = AT - timedelta(days=1)
            add("applications", id=application_id,
                application_number=f"DEMO-APP-2026-{app_no+1:06d}",
                institution_id=institution_id, campus_id=campus_id,
                application_type_id=uid("application_type", type_no),
                workflow_definition_id=uid("workflow", type_no), status=status,
                submitted_at=submitted, closed_at=closed, created_at=created,
                updated_at=closed or min(AT, created + timedelta(days=18)), version=1)
            stage_no = 0 if status == "draft" else 2 if status == "deficiency_returned" else 4 if status in ("approved", "closed", "rejected") else 1
            stage_id = uid("stage_instance", app_no)
            entered = submitted or created
            add("application_stage_instances", id=stage_id, application_id=application_id,
                workflow_stage_id=uid("stage", f"{type_no}-{stage_no}"),
                status="completed" if status in ("approved", "closed", "rejected") else "in_progress",
                entered_at=entered, completed_at=closed or min(AT, entered + timedelta(days=25))
                if status in ("approved", "closed", "rejected") else None,
                due_at=entered + timedelta(days=STAGES[stage_no][2]))
            if submitted:
                add("application_submissions", id=uid("submission", app_no), application_id=application_id,
                    submission_number=1, submitted_at=submitted,
                    submission_status="returned" if status == "deficiency_returned" else "submitted")

            for doc_no in range(2):
                doc_type_no = (app_no + doc_no * 2) % len(DOC_TYPES)
                document_id = uid("document", f"{app_no}-{doc_no}")
                version_id = uid("document_version", f"{app_no}-{doc_no}")
                issue = (created - timedelta(days=120 + app_no % 400)).date()
                expiry = issue + timedelta(days=365 + (app_no % 3) * 365) if DOC_TYPES[doc_type_no][2] else None
                doc_status = "expired" if expiry and expiry < AT.date() else "active"
                add("documents", id=document_id, institution_id=institution_id, campus_id=campus_id,
                    application_id=application_id, document_type_id=uid("document_type", doc_type_no),
                    document_scope="application", status=doc_status, created_at=created,
                    updated_at=created, version=1)
                add("document_versions", id=version_id, document_id=document_id, version_number=1,
                    object_key=f"demo/metadata-only/{app_no:06d}/{doc_no}.pdf",
                    file_name=f"DEMO_{DOC_TYPES[doc_type_no][0]}_{app_no+1:06d}.pdf",
                    mime_type="application/pdf", size_bytes=100000 + (app_no * 79 + doc_no * 101) % 750000,
                    sha256_hash=sha256(f"demo-placeholder-{app_no}-{doc_no}".encode()).hexdigest(),
                    uploaded_at=created + timedelta(hours=2), issue_date=issue, expiry_date=expiry,
                    verification_status=["pending", "needs_review", "verified"][app_no % 3])
                if doc_no == 0:
                    result = "warning" if app_no % 5 == 0 else "pass"
                    add("document_check_results", id=uid("document_check", app_no),
                        document_version_id=version_id, check_code="DEMO_METADATA_CHECK",
                        severity="medium" if result == "warning" else "info", result=result,
                        details=Jsonb({"demo_only": True, "note": "Synthetic check; no OCR or file validation ran"}),
                        review_status="pending")
                    if app_no % 2 == 0:
                        add("document_extractions", id=uid("extraction", app_no),
                            document_version_id=version_id, engine_name="DEMO_SYNTHETIC_NO_OCR",
                            status="needs_review", confidence_summary=Jsonb({"demo_only": True}),
                            extracted_fields=Jsonb({"demo_only": True, "file_processed": False}))

            if status == "deficiency_returned":
                notice_id = uid("deficiency_notice", app_no)
                add("deficiency_notices", id=notice_id, application_id=application_id,
                    stage_instance_id=stage_id, notice_number=1,
                    issued_at=entered + timedelta(days=5), response_due_at=entered + timedelta(days=35),
                    status="open")
                for item_no, description in enumerate(("Confirm the document type against the application category",
                                                       "Clarify the declared campus or facility details")):
                    add("deficiency_items", id=uid("deficiency_item", f"{app_no}-{item_no}"),
                        deficiency_notice_id=notice_id, criterion_code=f"DEMO-{item_no+1:02d}",
                        description=f"DEMO ONLY — {description}", resolution_status="pending")

            if app_no % 4 == 0 and status not in ("draft", "rejected", "closed"):
                add("evc_visits", id=uid("evc_visit", app_no), application_id=application_id,
                    campus_id=campus_id, status=["required", "committee_selection", "scheduling"][app_no % 3],
                    required_by=(submitted or created) + timedelta(days=90))
            if status in ("approved", "closed"):
                due = (submitted or created) + timedelta(days=120)
                add("compliance_conditions", id=uid("condition", app_no), application_id=application_id,
                    institution_id=institution_id, condition_code=f"DEMO-COND-{app_no+1:06d}",
                    description="DEMO ONLY — submit a dated facilities compliance update",
                    due_at=due, status="overdue" if due < AT else "open")

    for code, name in REPORTS:
        add("report_definitions", id=uid("report", code), report_code=f"DEMO-{code}",
            name=f"DEMO — {name}", version=1, enabled=False,
            access_policy=Jsonb({"demo_only": True, "approved": False}),
            columns_config=Jsonb({"demo_only": True, "report": name}),
            filters_config=Jsonb({"demo_only": True, "requires_policy_review": True}))


ORDER = ["regions", "application_types", "aph_rule_sets", "aph_rule_versions",
         "workflow_definitions", "workflow_stages", "workflow_transitions", "document_types",
         "institutions", "institution_campuses", "applications", "application_stage_instances",
         "application_submissions", "documents", "document_versions", "document_check_results",
         "document_extractions", "deficiency_notices", "deficiency_items", "evc_visits",
         "compliance_conditions", "report_definitions"]


def insert_rows(cursor, table, rows):
    columns = list(rows[0])
    statement = sql.SQL("INSERT INTO public.{} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns))
    cursor.executemany(statement, [tuple(row[column] for column in columns) for row in rows])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Insert the synthetic dataset in one transaction")
    args = parser.parse_args()
    build_rows()
    print("Synthetic DEMO rows planned:")
    for table in ORDER:
        print(f"  {table}: {len(ROWS[table])}")
    print("Total:", sum(len(ROWS[table]) for table in ORDER))
    if not args.apply:
        print("Preview only. Pass --apply to insert.")
        return

    url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing from the ignored root .env")
    with psycopg.connect(url, sslmode="require", connect_timeout=12,
                         options="-c statement_timeout=120000 -c lock_timeout=5000") as connection:
        if not connection.pgconn.ssl_in_use:
            raise RuntimeError("TLS database connection required")
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM public.institutions WHERE institution_code IS NULL OR institution_code NOT LIKE 'DEMO-%'")
            if cursor.fetchone()[0]:
                raise RuntimeError("Non-demo institutions exist; refusing to mix synthetic data")
            for table in ORDER:
                insert_rows(cursor, table, ROWS[table])
                print(f"Inserted/retained {table}: {len(ROWS[table])}")
            cursor.executemany(
                "UPDATE public.applications SET current_stage_instance_id = %s "
                "WHERE id = %s AND current_stage_instance_id IS NULL",
                [(uid("stage_instance", app_no), uid("application", app_no)) for app_no in range(1080)])
            cursor.executemany(
                "UPDATE public.documents SET current_version_id = %s "
                "WHERE id = %s AND current_version_id IS NULL",
                [(uid("document_version", f"{app_no}-{doc_no}"), uid("document", f"{app_no}-{doc_no}"))
                 for app_no in range(1080) for doc_no in range(2)])
        # psycopg commits the whole dataset only on successful context exit.
    print("Committed synthetic DEMO dataset. No Auth users, role grants, or actual files were created.")


if __name__ == "__main__":
    main()
