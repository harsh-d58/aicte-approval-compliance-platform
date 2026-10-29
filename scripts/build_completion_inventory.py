"""Build traceability inventories; never infer completion from source presence.

Run from the repository root: python scripts/build_completion_inventory.py
The API inventory imports the app only to inspect OpenAPI; it does not call routes.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PRD = ROOT / "Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md"
OUT = ROOT / "completion"


def owner(section, heading):
    if "Meeting-to-Record" in heading or section == "9.7":
        return "CP07"
    mapping = {"7.1": "CP04", "7.2": "CP10", "7.3": "CP06",
               "7.4": "CP08", "7.5": "CP08", "9.3": "CP04",
               "9.4": "CP06", "9.5": "CP06", "9.6": "CP06",
               "13.1": "CP01", "13.2": "CP05", "13.3": "CP07",
               "13.4": "CP02", "13.5": "CP02", "13.6": "CP13",
               "16.1": "CP03", "16.2": "CP06", "16.3": "CP09",
               "16.4": "CP05"}
    if section in mapping:
        return mapping[section]
    return {"1": "CP14", "2": "CP14", "3": "CP01", "4": "CP13",
            "5": "CP00", "6": "CP00", "7": "CP04", "8": "CP09",
            "9": "CP11", "10": "CP02", "11": "CP10", "12": "CP12",
            "13": "CP13", "14": "CP13", "15": "CP13", "16": "CP09",
            "17": "CP12", "18": "CP14", "19": "CP13", "20": "CP12",
            "21": "CP14", "22": "CP14"}.get(section.split(".")[0], "CP14")


def normalize_path(path):
    return re.sub(r"\{[^}]+\}", "{id}", path.removeprefix("/api/v1"))


def build():
    content = PRD.read_bytes()
    lines = content.decode("utf-8").splitlines()
    requirements, endpoints, sections = [], [], []
    section, heading = "1", "Product overview"
    fenced = False
    for number, line in enumerate(lines, 1):
        clean = line.strip()
        if clean.startswith("```"):
            fenced = not fenced
            continue
        if fenced or not clean:
            continue
        if clean.startswith("#"):
            normalized = clean.replace("\\.", ".")
            match = re.match(r"^#+\s+\*\*(\d+(?:\.\d+)*)\b", normalized)
            if match:
                section = match.group(1)
            heading = normalized.lstrip("# ").strip("*")
            if re.match(r"^#\s+\*\*\d+", clean):
                sections.append({"section": section, "title": heading,
                                 "source_line": number, "review_status": "UNASSESSED"})
            continue

        table = clean.startswith("|") and clean.endswith("|")
        if table:
            if re.fullmatch(r"[|:\-\s]+", clean):
                continue
            next_line = lines[number].strip() if number < len(lines) else ""
            if re.fullmatch(r"[|:\-\s]+", next_line) and "-" in next_line:
                continue
        bullet = bool(re.match(r"^(?:\*|-|\d+\.)\s+", clean))
        normative = bool(re.search(r"\b(must|should|require[sd]?|shall|cannot|only when|subject to|depends on)\b", clean, re.I))
        if not (table or bullet or normative):
            continue

        original = re.match(r"^\|\s*((?:WF|BR)-\d+)\s*\|", clean)
        ident = original.group(1) if original else f"PRD-L{number:04d}"
        priority = "NEEDS_CLASSIFICATION"
        if original and ident.startswith("BR-"):
            priority = "BUSINESS_RULE"
        elif re.search(r"\|\s*Must\s*\|", clean):
            priority = "MUST"
        elif re.search(r"\|\s*Should\s*\|", clean):
            priority = "SHOULD"
        elif section == "13.5" or "if enabled" in clean.lower():
            priority = "CONDITIONAL"

        requirements.append({
            "requirement_id": ident, "prd_section": section, "heading": heading,
            "source_line_start": number, "source_line_end": number,
            "source_text": clean, "kind": "table_row" if table else "list_item" if bullet else "normative_paragraph",
            "priority": priority, "primary_work_package": owner(section, heading),
            "status": "UNASSESSED", "applicability_decision": None,
            "implementation_references": [], "acceptance_tests": [],
            "negative_failure_tests": [], "migration_dependencies": [],
            "evidence": [], "release_revision": None, "acceptance_owner": None,
            "review_note": "Classify/split combined obligations; exact source is retained. Presence is not completion."
        })
        if section == "9.2" and table:
            match = re.match(r"^\|\s*(GET|POST|PATCH|PUT|DELETE)\s*\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|", clean)
            if match:
                method, path, purpose = match.groups()
                endpoints.append({"requirement_id": ident, "source_line": number,
                                  "group": heading, "method": method, "prd_path": path,
                                  "purpose": purpose, "acceptance_status": "UNASSESSED",
                                  "approved_equivalent": None, "evidence": []})

    from backend.app.main import app
    current = {(method.upper(), normalize_path(path))
               for path, operations in app.openapi()["paths"].items()
               for method in operations if method.lower() in {"get", "post", "patch", "put", "delete"}}
    for entry in endpoints:
        entry["exact_method_path_present"] = (entry["method"], normalize_path(entry["prd_path"])) in current
        entry["contract_action"] = "Test behavior and authorization" if entry["exact_method_path_present"] else "Implement contract or approve/document an equivalent API; not complete"

    metadata = {"generated_for": "FINAL_PRD_COMPLETION_PLAN.md", "date": "2026-10-29",
                "prd_file": PRD.name, "prd_sha256": sha256(content).hexdigest(),
                "status_policy": "No requirement is marked PASS by this generator."}
    OUT.mkdir(exist_ok=True)
    (OUT / "PRD_REQUIREMENT_LEDGER.json").write_text(json.dumps({**metadata, "sections": sections,
        "clause_count": len(requirements), "work_package_counts": dict(Counter(r["primary_work_package"] for r in requirements)),
        "requirements": requirements}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "PRD_API_COVERAGE.json").write_text(json.dumps({**metadata, "operation_count": len(endpoints),
        "exact_contracts_present": sum(e["exact_method_path_present"] for e in endpoints),
        "operations": endpoints}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert {r["requirement_id"] for r in requirements if r["requirement_id"].startswith("WF-")} == {f"WF-{n:02d}" for n in range(1, 11)}
    assert {r["requirement_id"] for r in requirements if r["requirement_id"].startswith("BR-")} == {f"BR-{n:02d}" for n in range(1, 25)}
    assert {s["section"] for s in sections} == {str(n) for n in range(1, 23)}
    assert len({r["requirement_id"] for r in requirements}) == len(requirements)
    print(f"Indexed {len(requirements)} source clauses, all 22 sections, WF-01..10 and BR-01..24")
    print(f"PRD API operations: {len(endpoints)}; exact method/path present: {sum(e['exact_method_path_present'] for e in endpoints)}")
    print("All acceptance statuses remain UNASSESSED. VERDICT: PASS")


if __name__ == "__main__":
    build()
