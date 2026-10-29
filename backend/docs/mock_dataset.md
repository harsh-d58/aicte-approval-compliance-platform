# Synthetic database dataset — 29 October 2026

The user requested a large realistic **mock** dataset in the connected database. [seed_mock_data.py](../seed_mock_data.py) inserted **10,211 deterministic rows across 22 public tables** in one transaction. The schema and existing records were not replaced. The script refuses to mix with any non-demo institution and can be rerun without duplicate rows (`UUIDv5` IDs and `ON CONFLICT DO NOTHING`).

| Area | Rows |
| --- | ---: |
| Regions | 12 |
| Institutions and campuses | 180 each |
| Application categories, sample rule sets/versions, workflows | 4 each |
| Workflow stages and transitions | 20 and 16 |
| Applications, current stage instances and submissions | 1,080; 1,080; 972 |
| Documents and metadata-only versions | 2,160 each |
| Synthetic document checks and extraction placeholders | 1,080 and 540 |
| Deficiency notices and items | 108 and 216 |
| EVC queue entries and open/overdue compliance conditions | 162 and 216 |
| Disabled definitions for the eight PRD reports | 8 |

All institution/application codes start with `DEMO-`. Names and addresses are invented. APH rules and workflows are marked **draft**; report definitions are disabled. Document `object_key` values point to `demo/metadata-only/...` and **no actual file exists**. Extraction rows use `DEMO_SYNTHETIC_NO_OCR`; no OCR engine processed a document. EVC entries have no selected experts or confirmed slots, and compliance conditions have no fabricated verification. These rows support UI/query development, not regulatory actions or official AICTE reporting.

No `auth.users`, `public.users`, roles, permissions, role assignments, notifications, evidence submissions, report runs or audit events were created. Live browser access still needs an authorised test login and approved scoped grants. The current API connection has `BYPASSRLS`; new business write routes remain gated as described in [manual_handoff.md](manual_handoff.md).

## Repeat or preview

From the repository root:

```powershell
.\.venv\Scripts\python.exe backend\seed_mock_data.py
.\.venv\Scripts\python.exe backend\seed_mock_data.py --apply
```

The first command previews planned counts. The second inserts any missing deterministic rows in one transaction. Do not edit the namespace or codes and rerun against the same database: that would create a second dataset. The script does not delete data.

## Verification

A read-only check found 180 institutions, 1,080 applications, 2,160 documents and versions, and all other counts above. Every demo application has a current stage instance; every document has a current version. There are zero non-demo institutions and zero Auth users, application users or role assignments. The seed transaction completed without foreign-key or check-constraint errors.
