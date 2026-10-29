# PRD completion inventories

These files support [the consolidated plan](../FINAL_PRD_COMPLETION_PLAN.md).

Generate from the repository root:

```text
.venv\Scripts\python.exe scripts\build_completion_inventory.py
```

`PRD_REQUIREMENT_LEDGER.json` indexes table rows, list items and normative paragraphs from the exact PRD source, retaining source lines and a SHA-256 hash. It includes source requirements and reference/configuration/acceptance items that still require human classification and splitting. Its clause count is not a count of separately mandatory product features.

`PRD_API_COVERAGE.json` compares PRD section 9.2 method/path contracts against current OpenAPI. Parameter names are normalized. A present route has **not** passed authorization, persistence, concurrency or end-to-end acceptance. An absent exact contract may have an equivalent implementation; document and approve that mapping instead of silently counting a command bridge as the specified API.

All generated acceptance statuses start `UNASSESSED`. Attach actual evidence during implementation. Do not promote status from a filename, test count, build result, phase label or test with mocked providers.

Before regenerating after implementation starts, preserve and merge reviewed statuses/evidence. The generator rebuilds the source inventory; it is not a migration tool for manually curated evidence. If the PRD changes, compare source hashes and review the diff rather than carrying forward old passes automatically.

The source PRD, user instruction to remove simulated operational behavior, and the consolidated plan govern applicability. Mock fixtures may remain in isolated tests; they must not produce production business success. Official policy decisions and enabled external integrations need their own evidence.
