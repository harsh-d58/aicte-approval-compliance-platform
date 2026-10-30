# Phase 03 correction evidence — 30 October 2026

The form sent documentVersionIds but the live bridge read versionIds and omitted
document_version_id in each item response. The server correctly rejected a
document reference without an exact version. The generic picker also exposed
other applications' documents from the same institution.

The form now provides one compatible version selector per unresolved item. It
matches institution/application scope and the mandated document category, retains
pending versions for human review, excludes rejected versions, and transmits the
selected document and exact version IDs. Resolved items are not overwritten.

Upload links preselect the application and institution, keep the document category
where known, and return to the active notice. A document from a sibling case is
not reused as an upload target. Existing evidence and submissions are unchanged.

Follow-up: the correction action is now an inline local file picker rather than
a navigation link. Selecting a local PDF/PNG/JPEG reveals the upload confirmation
on the same notice. The real document upload command persists the bytes and its
refreshed immutable version is automatically selected for the item. The narrative
form stays mounted. No application-creation route is involved.

Review follow-up: Accept/Reject controls require RESPONDED, matching the server's
submitted-response guard. Click errors are caught and shown inline with refresh,
instead of becoming unhandled runtime errors. Batch review skips OPEN/RESOLVED
items and gives each submitted item its own idempotency key. Server retry bodies
include item_id so cached results cannot be reused for a different item.

Live browser investigation also found initial workspace loading could remain true
when polling started another request before the first snapshot finished. Loading
now ends on an accepted same-identity response; older overlapping responses cannot
replace a newer accepted snapshot.

Fresh checks: 35 frontend tests, 8 backend deficiency tests, TypeScript and the
production build pass. The isolated Edge smoke test did not reach the notice:
it timed out on Preparing your workspace, without a JavaScript page error.
Do not count the native file picker/live notice journey as browser-verified.
See tmp/phase3-local-upload-browser.log for that limitation.

A read-only database check found no document reference or filename matching
DFS/HQ/2026/FSC/8842. That value in the voice-over is a placeholder, not an
uploaded renewed certificate. The operator must upload the intended test file
before selecting it; entering its reference in a narrative does not create bytes.

Regression checks cover the actual live command payload, case/category filtering,
different per-item versions, resolved items, and missing selections. See
tmp/phase3-frontend-tests.log and tmp/phase3-build.log for fresh execution output.
Backend deficiency guards remain enforced; no evidence verification was fabricated.
