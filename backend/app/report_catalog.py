"""Typed output contracts for the eight PRD reports; these are not business rows."""
from hashlib import sha256
import json

REPORT_COLUMNS = {
    "region-performance": ["Region", "Received", "Completed", "Stage pendency", "Processing time", "Overdue", "EVC completion", "Compliance"],
    "application-pendency": ["Application", "Institution", "Stage", "Stage age", "Application age", "Deadline", "Overdue duration", "Owner", "Next action"],
    "evc-status": ["Application", "Selected committee", "Proposed date", "Confirmed date", "Scheduling status", "Deadline", "Conflicts", "Visit status", "Report status"],
    "undertaking-compliance": ["Condition", "Due date", "Evidence status", "Verification status", "Overdue days", "Reviewer", "Escalation"],
    "document-validity": ["Institution", "Document type", "Issue date", "Expiry date", "Version", "Verification status", "Renewal status"],
    "overdue-actions": ["Entity type", "Case", "Action", "Owner", "Due date", "Overdue duration", "Escalation level", "Resolution"],
    "notification-delivery": ["Event", "Recipient category", "Channel", "Delivery status", "Attempt count", "Failure reason", "Last attempt"],
    "case-closure": ["Application", "Closure date", "Final status", "Closure authority", "Reason", "Duration", "Reopen status"],
}
DATE_GRAINS = {
    "region-performance": "application submission", "application-pendency": "application submission",
    "evc-status": "confirmed visit start, otherwise required-by date",
    "undertaking-compliance": "condition due date", "document-validity": "current-version expiry date",
    "overdue-actions": "action due date", "notification-delivery": "notification creation",
    "case-closure": "case closure",
}


def normalize_code(value):
    return value.removeprefix("DEMO-").lower().replace("_", "-")


def contract_columns(code):
    return REPORT_COLUMNS[normalize_code(code)]


def snapshot_digest(rows, *, columns, period, code):
    body = {"code": normalize_code(code), "columns": columns, "period": period, "rows": rows}
    return sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def validate_rows(code, rows):
    columns = contract_columns(code)
    for row in rows:
        if set(row) != set(columns):
            raise ValueError("Report output does not match its published column contract")
    return columns
