# **Product Requirements Document (PRD)**

## **AICTE Approval Workflow Automation and Institutional Compliance Monitoring Platform**

**Project:** SIH 2026 Finals  
**Document type:** Product Requirements Document  
**Version:** 1.0  
**Status:** Proposed product specification for prototype and implementation planning  
**Primary users:** AICTE administrators, regional officers, scrutiny officers, EVC coordinators and experts, compliance officers, authorised institutional representatives, auditors, and system administrators.

---

# **1\. Product Overview**

## **1.1 Purpose**

This document defines the product requirements, business rules, data model, entity relationships, user workflows, API contracts, access controls, reporting, technical architecture, security requirements, and acceptance criteria for an integrated platform supporting AICTE approval workflow automation and institutional compliance monitoring.

The platform will manage an application from intake through prescribed review stages, inspections where required, approval-related activities, time-bound undertakings, document renewals, and case closure.

The system will automate administrative tasks where permitted while retaining human control over statutory scrutiny, expert selection, inspection findings, document verification, and approval decisions.

## **1.2 Product goals**

The product must:

1. Route applications through configurable, APH-prescribed workflows.  
2. Track stage ownership, ageing, deadlines, pending actions, and bottlenecks.  
3. Support authorised deficiency returns and resubmissions.  
4. Provide dashboards tailored to users' roles and organisational scope.  
5. Manage EVC queues, committee assignments, scheduling, invitations, visits, and reports.  
6. Track undertakings, evidence submissions, verification, and closure.  
7. Track document validity, renewals, and overdue actions.  
8. Send configurable notifications, reminders, and escalations.  
9. Generate eight categories of consolidated downloadable reports.  
10. Maintain a complete, traceable audit history.  
11. Integrate with existing authorised AICTE systems where approved interfaces are available.  
12. Provide two additional innovations: a tamper-evident audit layer and an EVC Committee Coordination and Meeting-to-Record Assistant.

## **1.3 Five core modules**

| ID | Core module | Primary responsibility |
| ----- | ----- | ----- |
| M1 | Workflow Automation Engine | Application routing, stage transitions, assignments, deficiency returns, and case history |
| M2 | Role-Based Dashboards | Status, workload, ageing, deadlines, bottlenecks, and performance views |
| M3 | EVC Scheduling and Management | EVC queues, committee assignment records, schedules, invitations, visits, and reports |
| M4 | Undertaking and Compliance Tracker | Time-bound conditions, evidence submissions, verification, and compliance closure |
| M5 | Document Expiry and Renewal Alerts | Document registry, validity, expiry reminders, renewals, and verification |

The institutional master profile, OCR document checks, notifications, audit, and reporting are shared capabilities supporting these modules. They are not additional core modules.

## **1.4 Principal innovations**

### **Innovation 1: Blockchain-Backed Tamper-Evident Audit Trail**

An optional permissioned audit layer will record hashes and minimal metadata for selected workflow events and approved records. It will help authorised stakeholders detect whether content has changed since its fingerprint was recorded.

Documents, personal information, committee recordings, and other sensitive content must remain off-chain.

Blockchain is optional. If AICTE is the sole trusted record operator, an append-only, hash-chained audit log, digital signatures, and protected backups may be sufficient.

### **Innovation 2: EVC Committee Coordination and Meeting-to-Record Assistant**

The authorised regional officer or designated authority selects the required 4–5 experts for a particular EVC. The system then checks the schedules of those exact experts and the institution, identifies common available slots within the prescribed deadline, explains recommendations, and manages the confirmed meeting.

After the visit, the assistant prepares draft minutes, criterion-wise observations, action items, and an EVC report from authorised inputs for committee review and approval.

The system does not select experts, independently change committee membership, invent findings, or make statutory decisions.

---

# **2\. Scope and Assumptions**

## **2.1 In scope**

* Institution profiles and authorised institutional users.  
* Application intake, import, and workflow routing.  
* APH-configurable workflow definitions and versions.  
* Scrutiny assignments, observations, deficiency notices, and resubmissions.  
* Role-based dashboards.  
* EVC queues, committee assignments, expert availability, scheduling, invitations, and completion.  
* EVC meeting-record drafts and approval.  
* Undertakings, evidence submissions, verification, and escalation.  
* Document registry, OCR-assisted checks, expiry, renewal, and verification.  
* Notifications and delivery tracking.  
* Eight consolidated report categories.  
* Digital audit trail and optional blockchain anchoring.  
* Approved integrations with existing AICTE or other authorised systems.  
* Administrative configuration, monitoring, security, and audit.

## **2.2 Out of scope for the initial prototype**

* Replacing the existing AICTE portal without a formal migration decision.  
* Automatically approving or rejecting statutory applications using AI.  
* Automatically choosing EVC experts or replacing committee members.  
* Treating OCR output as proof of document authenticity.  
* Assuming every expert has an accessible calendar API.  
* Assuming every document type has an expiry date.  
* Building student application submission workflows; this product concerns regulatory applications submitted by authorised institutional representatives.  
* Deploying a production blockchain before its governance, value, and operating model are approved.  
* Integrating external systems without authorised API access or data-sharing approval.

## **2.3 Requirements versus assumptions**

| Item | Status |
| ----- | ----- |
| Five core modules | Confirmed product scope |
| EVC expert selection by an authorised officer | Confirmed product rule |
| Scheduling against the exact selected experts' availability | Confirmed innovation requirement |
| Draft EVC minutes and reports with human approval | Confirmed innovation requirement |
| Eight consolidated report categories | Confirmed product requirement |
| APH routing examples | Must be configured and verified against the applicable APH |
| Required EVC committee size | The product must support the required 4–5 experts for the intended process; final rules must be validated |
| Calendar integration | Depends on approved access; manual availability submission is the fallback |
| Existing AICTE APIs | Unknown until integration discovery |
| Production workload and performance targets | Must be validated using current operational data |
| Blockchain deployment | Optional, subject to governance and security review |

The final APH rules, stage conditions, deadlines, document requirements, and escalation policies must be signed off by authorised policy owners before production use.

---

# **3\. Stakeholders, Personas, and Permissions**

## **3.1 User personas**

| Persona | Main responsibilities | Typical actions |
| ----- | ----- | ----- |
| Institutional representative | Submit and maintain institution records | Submit application, respond to deficiencies, upload evidence, renew documents |
| Scrutiny officer | Review applications and supporting documents | Inspect documents, add observations, return deficiencies, recommend next steps |
| Regional officer | Oversee regional cases and coordinate EVC processes | Assign cases, select EVC experts, monitor deadlines, approve scheduling |
| EVC coordinator | Coordinate committee logistics | Manage availability, recommend slots, send invitations, track visit completion |
| EVC expert | Participate in an assigned committee | Submit availability, review authorised material, record observations, review drafts |
| Compliance officer | Monitor approval conditions and evidence | Review evidence, verify compliance, request clarification, close conditions |
| Central administrator | Monitor performance across regions | View aggregate dashboards, manage authorised configuration |
| Policy/configuration administrator | Maintain approved rules | Publish workflow versions, update deadlines, manage controlled configuration |
| Auditor | Inspect authorised records and audit history | Review actions, verify record integrity, export authorised audit reports |
| System administrator | Operate technical services | Manage deployment, monitoring, backups, identity integration, and service health |
| Integration service | Exchange data with approved systems | Import applications, synchronise permitted records, report integration failures |

## **3.2 Role and scope model**

A user's role determines what actions they can perform. Their scope determines which records they can access.

A role alone must not grant unrestricted access to every institution or region.

Examples:

* An institutional representative may access only the institutions they are authorised to represent.  
* A regional officer may access cases within their assigned regional scope.  
* A scrutiny officer may access assigned cases and authorised supporting records.  
* An EVC expert may access the relevant EVC material for their assigned committee, not all institutional records.  
* A compliance officer may access the conditions and evidence within their assigned scope.  
* An auditor may have read access to authorised historical records and audit events, without permission to change workflow state.

## **3.3 Permission categories**

| Permission category | Example actions |
| ----- | ----- |
| Read | View a case, document metadata, schedule, or report |
| Create | Create an application draft, deficiency notice, or evidence submission |
| Update | Edit permitted profile fields or draft observations |
| Assign | Assign cases or record committee membership |
| Transition | Move an application to a permitted next stage |
| Return | Return an application for deficiencies with reasons |
| Verify | Verify evidence or documents |
| Approve | Approve a decision record or final EVC report |
| Configure | Publish workflow or escalation rule versions |
| Export | Download reports or audit records |
| Administer | Manage users, integrations, and system configuration |

All privileged actions must be enforced by the backend, not merely hidden in the user interface.

---

# **4\. System Overview and Architecture**

## **4.1 Proposed architecture**

Use a modular monolith for the initial implementation. Keep the business logic in well-defined modules within one deployable backend. This is simpler to test and operate than introducing microservices before there is a demonstrated need.

Authorised Users  
      \|  
      v  
Web / Mobile-Friendly Interface  
      \|  
      v  
API Gateway / Application Backend  
      \|  
      \+-- Identity and Access Control  
      \+-- Workflow Engine  
      \+-- Institution and Application Services  
      \+-- Document and OCR Services  
      \+-- EVC Scheduling and Meeting Records  
      \+-- Undertaking and Compliance Services  
      \+-- Notification and Escalation Services  
      \+-- Reporting Services  
      \+-- Audit Services  
      \|  
      \+--------------------+  
      \|                    \|  
      v                    v  
PostgreSQL Database    Encrypted Object Storage  
      \|  
      v  
Background Job Queue  
      \|  
      \+-- OCR Processing  
      \+-- Deadline Checks  
      \+-- Notifications and Retries  
      \+-- Calendar Synchronisation  
      \+-- Report Generation  
      \+-- Audit Hash Anchoring  
      \|  
      v  
Approved External Integrations  
(Calendar, Email/SMS, Existing AICTE Systems)

The database is the authoritative source for application and workflow state. Background jobs and external integrations must not independently change statutory state without passing through the backend's validation rules.

## **4.2 Proposed technology stack**

| Layer | Proposed technology | Purpose |
| ----- | ----- | ----- |
| Frontend | Next.js, React, TypeScript | Responsive dashboards, forms, case management |
| Backend | Python FastAPI | APIs, validation, business logic, workflow transitions |
| Database | PostgreSQL | Structured records, relationships, workflow state, reporting data |
| Background jobs | Redis and Celery | OCR, notifications, deadline checks, exports, sync jobs |
| File storage | Encrypted, versioned object storage | PDFs, images, supporting evidence, approved reports |
| OCR | PaddleOCR or Tesseract | Extract text from scanned documents |
| Authentication | Keycloak for prototype | Identity and access management |
| Future identity integration | Approved AICTE or government SSO | Production identity integration where available |
| Notifications | Email, SMS, in-platform adapters | Configurable communications |
| Calendar | Approved calendar APIs or controlled availability entry | EVC scheduling |
| Monitoring | Prometheus and Grafana | Service health, job metrics, alerting |
| Deployment | Docker | Reproducible development and deployment |
| Optional ledger | Hyperledger Fabric or equivalent permissioned system | Cross-organisation audit verification, if justified |

Production hosting must use an approved government cloud or other authorised environment, subject to applicable security, procurement, and organisational approval.

---

# **5\. Core Entity Model**

This section defines the principal entities, their responsibilities, and their relationships. The table definitions are logical models; exact SQL types and naming can be adapted during implementation.

## **5.1 Entity conventions**

Unless otherwise stated, entities should use:

* `id`: primary key, preferably UUID.  
* `created_at`: creation timestamp.  
* `created_by`: creating user or service.  
* `updated_at`: last update timestamp.  
* `updated_by`: last updating user or service.  
* `version`: optimistic concurrency version for records that can be edited.  
* `status`: where a lifecycle is applicable.

Do not store large file contents directly in PostgreSQL. Store files in protected object storage and keep their metadata in the database.

## **5.2 Organisation and access entities**

| Entity/table | Purpose | Important fields | Relationships and constraints |
| ----- | ----- | ----- | ----- |
| `institutions` | Main institution record | `id`, `official_name`, `institution_code`, `institution_type`, `status`, `region_id` | One institution has many campuses, users, applications, and documents. Institution code should be unique where a reliable code exists. |
| `institution_campuses` | Physical campus records | `id`, `institution_id`, `campus_name`, `address`, `region_id`, `is_primary` | Many campuses belong to one institution. |
| `institution_profile_attributes` | Structured extensible profile data | `id`, `institution_id`, `attribute_key`, `value_text`, `value_date`, `value_number`, `source_document_id`, `verified_status` | One institution has many attributes. Use typed fields and a controlled attribute catalogue rather than one unrestricted JSON object for everything. |
| `regions` | Regional hierarchy and reporting scope | `id`, `code`, `name`, `parent_region_id`, `status` | A region may have child regions and many institutions/users. |
| `users` | Authenticated human or service identities | `id`, `identity_subject`, `display_name`, `email`, `phone`, `status`, `last_login_at` | Users receive roles through assignments. Identity subject should be unique within the configured identity provider. |
| `roles` | Named role definitions | `id`, `role_code`, `role_name`, `description` | Roles map to permissions. |
| `permissions` | Granular actions | `id`, `permission_code`, `description` | Permissions are linked to roles through `role_permissions`. |
| `role_permissions` | Role-to-permission mapping | `role_id`, `permission_id` | Composite primary key prevents duplicate mappings. |
| `user_role_assignments` | Role granted to a user within a scope | `id`, `user_id`, `role_id`, `scope_type`, `scope_id`, `valid_from`, `valid_until`, `status` | A user can hold multiple scoped roles. Backend must validate scope on every request. |
| `expert_profiles` | Expert information for EVC participation | `id`, `user_id`, `expertise`, `eligibility_status`, `availability_method` | An expert profile is associated with a user. Sensitive personal information should be minimised. |
| `integration_endpoints` | Approved external system configurations | `id`, `system_name`, `integration_type`, `environment`, `status`, `secret_reference` | Credentials must be stored in a secret manager, not as plaintext database values. |
| `sync_jobs` | Track import/export jobs | `id`, `integration_endpoint_id`, `job_type`, `status`, `started_at`, `completed_at`, `error_summary` | One integration can have many sync jobs. |

### **Important access design**

Institutional representatives must not gain access to an institution merely by entering its name or code. Their relationship to the institution must be explicitly authorised and represented through scoped access assignments or an equivalent controlled relationship.

## **5.3 Application and workflow entities**

| Entity/table | Purpose | Important fields | Relationships and constraints |
| ----- | ----- | ----- | ----- |
| `application_types` | Defines application categories | `id`, `code`, `name`, `description`, `status` | One type may be used by many applications and workflow definitions. |
| `applications` | Main regulatory application | `id`, `application_number`, `institution_id`, `campus_id`, `application_type_id`, `status`, `current_stage_instance_id`, `submitted_at`, `closed_at` | Each application belongs to an institution and has many submissions, stage records, documents, and audit events. Application number should be unique. |
| `application_submissions` | A submitted version of an application | `id`, `application_id`, `submission_number`, `submitted_by`, `submitted_at`, `submission_status` | One application has multiple submissions or resubmissions. |
| `aph_rule_sets` | Identifies the applicable regulatory rule set | `id`, `rule_set_code`, `title`, `source_reference`, `effective_from`, `effective_until`, `status` | Rule sets can have versions and be linked to workflow definitions. |
| `aph_rule_versions` | Versioned approved rule content | `id`, `rule_set_id`, `version_number`, `approved_by`, `approved_at`, `content_reference`, `checksum` | Published versions are immutable; changes create a new version. |
| `workflow_definitions` | Defines an approval pathway | `id`, `name`, `application_type_id`, `aph_rule_version_id`, `status`, `version_number` | A workflow definition belongs to a rule version and can be used by many applications. |
| `workflow_stages` | Defines stages within a workflow | `id`, `workflow_definition_id`, `stage_code`, `stage_name`, `stage_order`, `stage_type`, `default_sla_days` | Stage code must be unique within its workflow definition. |
| `workflow_transitions` | Defines allowed stage transitions | `id`, `workflow_definition_id`, `from_stage_id`, `to_stage_id`, `transition_type`, `guard_rule`, `requires_authorisation` | Both stage references must belong to the same workflow definition. |
| `application_stage_instances` | Tracks an application's actual stage | `id`, `application_id`, `workflow_stage_id`, `status`, `entered_at`, `completed_at`, `due_at`, `assigned_role_id` | One application has many stage instances over time. |
| `stage_history` | Immutable history of stage changes | `id`, `application_id`, `from_stage_id`, `to_stage_id`, `actor_user_id`, `reason`, `event_at`, `correlation_id` | Each transition generates a history record. |
| `assignments` | Assigns a case or task to a person or team | `id`, `application_id`, `stage_instance_id`, `assigned_user_id`, `assigned_role_id`, `assigned_at`, `due_at`, `status` | Assignments can be reassigned, but the history must be retained. |
| `deficiency_notices` | Groups deficiencies returned to an institution | `id`, `application_id`, `stage_instance_id`, `notice_number`, `issued_by`, `issued_at`, `response_due_at`, `status` | One notice has multiple deficiency items. |
| `deficiency_items` | Individual deficiency requirements | `id`, `deficiency_notice_id`, `criterion_code`, `description`, `related_document_id`, `resolution_status` | Each item belongs to a notice and may refer to a document or criterion. |
| `approval_decisions` | Records authorised formal outcomes | `id`, `application_id`, `decision_type`, `decision_status`, `decision_authority`, `decision_at`, `reason`, `record_document_id` | Only authorised roles may create or approve decision records. |
| `configuration_changes` | Tracks controlled configuration changes | `id`, `configuration_type`, `object_id`, `old_version`, `new_version`, `approved_by`, `effective_at` | Every material workflow/rule change must be traceable. |

### **Workflow design rule**

An application must retain the workflow definition and APH rule version used when it entered the process. A later rule publication must not silently rewrite the historical route of an existing application.

If a rule change affects in-progress cases, the migration policy must be explicitly configured and approved.

## **5.4 Document and OCR entities**

| Entity/table | Purpose | Important fields | Relationships and constraints |
| ----- | ----- | ----- | ----- |
| `document_types` | Catalogue of document categories | `id`, `document_type_code`, `name`, `description`, `supports_expiry` | Defines recognised types and applicable metadata. |
| `document_requirement_rules` | Defines required documents by application context | `id`, `aph_rule_version_id`, `application_type_id`, `institution_type`, `document_type_id`, `required_condition` | Rules may vary by application type and institution type. Requirements must be configurable. |
| `documents` | Logical document record | `id`, `institution_id`, `campus_id`, `document_type_id`, `document_scope`, `status`, `current_version_id` | One logical document can have many versions. |
| `document_versions` | Immutable uploaded file versions | `id`, `document_id`, `version_number`, `object_key`, `file_name`, `mime_type`, `size_bytes`, `sha256_hash`, `uploaded_by`, `uploaded_at`, `issue_date`, `expiry_date`, `verification_status` | Each version points to a protected object-storage file. Do not overwrite previous versions. |
| `document_extractions` | OCR results | `id`, `document_version_id`, `engine_name`, `engine_version`, `status`, `confidence_summary`, `extracted_fields`, `completed_at` | OCR output must retain provenance and must not be treated as verified truth. |
| `document_check_results` | Validation outcomes | `id`, `document_version_id`, `check_code`, `severity`, `result`, `details`, `review_status`, `reviewed_by` | Records individual mismatch, missing field, expiry, or quality checks. |
| `file_attachments` | Reusable attachment metadata | `id`, `object_key`, `file_name`, `mime_type`, `size_bytes`, `hash`, `classification`, `malware_scan_status` | Can be linked to notices, reports, submissions, or evidence through explicit foreign keys or attachment association tables. |

### **Document rules**

* A file upload creates a new version; it does not overwrite an old version.  
* Expiry alerts are generated only when the document type and applicable rules support an expiry date.  
* Missing or uncertain OCR fields are flagged for review.  
* Document authenticity must be established through an authorised verification process, not through OCR or a hash alone.  
* Access to files must be checked independently of access to the parent application.

## **5.5 EVC and scheduling entities**

| Entity/table | Purpose | Important fields | Relationships and constraints |
| ----- | ----- | ----- | ----- |
| `committee_types` | Defines committee categories | `id`, `code`, `name`, `description` | Examples include relevant expert visit or other prescribed committees. |
| `committees` | Reusable committee or committee configuration record | `id`, `committee_type_id`, `name`, `status` | Distinguish a reusable committee definition from a committee assembled for a specific EVC. |
| `evc_visits` | Represents an EVC required for an application | `id`, `application_id`, `campus_id`, `status`, `required_by`, `confirmed_start_at`, `confirmed_end_at`, `completed_at`, `coordinator_user_id` | An application may have zero or more EVC visits depending on its workflow. |
| `evc_committee_members` | Records the exact experts selected for one EVC | `id`, `evc_visit_id`, `expert_user_id`, `committee_role`, `selection_status`, `selected_by`, `selected_at`, `replacement_reason` | Each row represents one selected expert. Enforce no duplicate active member per EVC. Required member count is configured according to applicable rules; the intended process supports 4–5 experts. |
| `expert_availability` | Availability supplied by an expert | `id`, `expert_user_id`, `start_at`, `end_at`, `availability_status`, `source`, `last_confirmed_at` | Stores available or unavailable intervals and provenance. |
| `calendar_connections` | Tracks approved calendar integration | `id`, `user_id`, `provider`, `connection_status`, `last_sync_at`, `credential_reference` | Tokens must be stored securely outside ordinary database fields. |
| `calendar_busy_blocks` | Represents known busy periods | `id`, `user_id`, `start_at`, `end_at`, `source`, `external_event_reference`, `last_synced_at` | Used for conflict checks. Sensitive event titles should not be collected unless necessary and authorised. |
| `slot_recommendations` | Stores scheduling proposals | `id`, `evc_visit_id`, `start_at`, `end_at`, `rank`, `feasibility_status`, `explanation`, `availability_snapshot_at`, `expires_at` | Recommendations are provisional and must be revalidated before confirmation. |
| `evc_invitations` | Records participant invitations | `id`, `evc_visit_id`, `recipient_user_id`, `sent_at`, `response_status`, `delivery_status` | A visit can have many invitations. |
| `evc_visit_events` | Tracks visit lifecycle events | `id`, `evc_visit_id`, `event_type`, `event_at`, `actor_user_id`, `reason`, `details` | Append-only event history for confirmation, rescheduling, postponement, completion, and cancellation. |
| `evc_observations` | Stores structured inspection observations | `id`, `evc_visit_id`, `criterion_code`, `observation_text`, `source_type`, `created_by`, `review_status` | Observations must be linked to authorised inputs and relevant criteria. |
| `evc_reports` | Stores EVC report records | `id`, `evc_visit_id`, `report_status`, `template_version`, `current_version_id`, `approved_by`, `approved_at` | One visit may have draft and approved report versions. |
| `meeting_record_versions` | Stores draft and final record versions | `id`, `evc_report_id`, `record_type`, `version_number`, `content_reference`, `source_manifest`, `created_by`, `approval_status`, `approved_by`, `approved_at` | Approved versions are immutable; edits create a new version. |
| `meeting_record_sources` | Links record sections to source inputs | `id`, `meeting_record_version_id`, `source_type`, `source_id`, `section_reference` | Supports traceability from draft statements to authorised notes or inputs. |
| `action_items` | Records follow-up actions from EVC | `id`, `evc_visit_id`, `description`, `responsible_role_id`, `due_at`, `status`, `source_observation_id` | An action may link to an observation or report section. |

### **Committee selection constraint**

For each EVC, only the authorised regional officer or another designated role may select or replace members. The selected experts must be stored explicitly in `evc_committee_members`.

The scheduler must check the availability of those exact active members. It must never silently substitute another expert because the original member is unavailable.

## **5.6 Undertaking and compliance entities**

| Entity/table | Purpose | Important fields | Relationships and constraints |
| ----- | ----- | ----- | ----- |
| `compliance_conditions` | Defines a condition that an institution must fulfil | `id`, `application_id`, `institution_id`, `condition_code`, `description`, `source_approval_id`, `due_at`, `status`, `verification_role_id` | One application or approval may create multiple conditions. |
| `evidence_submissions` | Records institution evidence | `id`, `compliance_condition_id`, `submitted_by`, `submitted_at`, `submission_number`, `status`, `response_to_verification_id` | Multiple submissions may exist for a condition. |
| `evidence_submission_files` | Links files to evidence submissions | `evidence_submission_id`, `document_version_id` | Many-to-many relationship between submissions and document versions where required. |
| `compliance_verifications` | Records review of evidence | `id`, `evidence_submission_id`, `reviewer_user_id`, `result`, `comments`, `verified_at` | One submission may have multiple verification attempts. |
| `document_renewal_cases` | Tracks renewal workflow | `id`, `document_id`, `current_version_id`, `renewal_due_at`, `status`, `assigned_to`, `closed_at` | One logical document can have multiple renewal cases over time. |

### **Compliance rules**

* Submission and verification are separate events.  
* A condition is closed only after the required evidence has been accepted by an authorised reviewer or an approved closure rule is satisfied.  
* Rejected or incomplete evidence must retain the reviewer’s reason.  
* Reopening a closed condition requires an authorised action and a recorded reason.

## **5.7 Notifications, escalation, reporting, and audit entities**

| Entity/table | Purpose | Important fields | Relationships and constraints |
| ----- | ----- | ----- | ----- |
| `notification_rules` | Defines notification triggers | `id`, `event_code`, `channel`, `recipient_rule`, `template_version`, `enabled` | Version and approve changes to notification policies where required. |
| `notifications` | Represents one logical notification | `id`, `event_code`, `recipient_user_id`, `related_entity_type`, `related_entity_id`, `created_at`, `status` | A notification can have multiple delivery attempts. |
| `notification_attempts` | Records delivery attempts | `id`, `notification_id`, `channel`, `attempt_number`, `attempted_at`, `result`, `provider_reference`, `failure_reason` | Each retry creates a new attempt record. |
| `escalation_rules` | Defines overdue escalation logic | `id`, `event_code`, `threshold_minutes`, `recipient_role_id`, `action_type`, `enabled` | Rules should be configurable and versioned. |
| `escalation_events` | Records a triggered escalation | `id`, `rule_id`, `related_entity_type`, `related_entity_id`, `triggered_at`, `recipient_user_id`, `resolution_status` | Prevent duplicate active escalations for the same rule and event window. |
| `report_definitions` | Defines report columns, filters, and permissions | `id`, `report_code`, `name`, `version`, `access_policy` | The eight required report types must be registered here or in an equivalent configuration. |
| `report_runs` | Tracks a report execution | `id`, `report_definition_id`, `requested_by`, `filters`, `started_at`, `completed_at`, `status`, `output_file_id` | Store a report snapshot or clear generation metadata. |
| `audit_events` | Append-only business audit log | `id`, `actor_id`, `action`, `entity_type`, `entity_id`, `event_at`, `correlation_id`, `reason`, `metadata`, `previous_hash`, `event_hash` | Restrict update/delete permissions. Sensitive values must not be copied into audit metadata. |
| `audit_anchors` | Tracks optional blockchain anchoring | `id`, `audit_event_id`, `ledger_network`, `transaction_reference`, `anchored_at`, `anchor_status` | Stores minimal references and hashes, not source documents. |
| `background_jobs` | Tracks asynchronous tasks | `id`, `job_type`, `related_entity_type`, `related_entity_id`, `status`, `attempt_count`, `next_attempt_at`, `last_error` | Supports retry and operational monitoring. |
| `system_settings` | Controlled application settings | `id`, `setting_key`, `setting_value`, `version`, `effective_at`, `approved_by` | Sensitive secrets must not be stored here as plaintext. |

---

# **6\. Entity Relationships and ER Model**

## **6.1 Main relationships**

| Parent entity | Relationship | Child entity | Cardinality |
| ----- | ----- | ----- | ----- |
| Institution | Has campuses | Institution campus | 1 to many |
| Institution | Submits | Application | 1 to many |
| Application | Uses | Workflow definition version | Many to 1 |
| Workflow definition | Contains | Workflow stages | 1 to many |
| Workflow stage | Defines | Workflow transitions | 1 to many |
| Application | Has | Stage instances/history | 1 to many |
| Application | Has | Deficiency notices | 1 to many |
| Deficiency notice | Contains | Deficiency items | 1 to many |
| Application | Has | Documents/submissions | 1 to many |
| Document | Has versions | Document version | 1 to many |
| Document version | Has | OCR results/checks | 1 to many |
| Application | May require | EVC visit | 1 to many |
| EVC visit | Has selected members | EVC committee members | 1 to many |
| Expert | Provides | Availability intervals | 1 to many |
| EVC visit | Has | Slot recommendations | 1 to many |
| EVC visit | Has | Invitations and visit events | 1 to many |
| EVC visit | Produces | Observations and report versions | 1 to many |
| Application/approval | Creates | Compliance conditions | 1 to many |
| Compliance condition | Receives | Evidence submissions | 1 to many |
| Evidence submission | Has | Verification records | 1 to many |
| Document | Has | Renewal cases | 1 to many |
| Notification | Has | Delivery attempts | 1 to many |
| User | Has | Role assignments | 1 to many |
| Role | Grants | Permissions | Many to many |
| User | Has scoped role | Institution/region/case | Many to many through assignments |
| Audit event | May be anchored by | Audit anchor | 1 to 0..1 or many, depending on anchoring strategy |

## **6.2 Relationship principles**

1. **Institution is not the user.** An institution is an organisation record. People access it through authorised user relationships.  
2. **Application is the central case record.** Workflow, documents, EVC, compliance, and decisions reference the application or its approval.  
3. **Workflow definition is versioned.** Each application retains the version used for routing.  
4. **Committee template and EVC committee assignment are different.** The selected experts for a particular visit must be stored in visit-specific membership rows.  
5. **Document and document version are different.** A logical document can have multiple immutable file versions.  
6. **Evidence submission and verification are different.** Uploading evidence does not automatically close a condition.  
7. **Notification and delivery attempt are different.** One notification may have multiple retries.  
8. **Draft and approved report versions are different.** Approval freezes a version; corrections produce a new version.  
9. **Audit events are append-only.** Corrections should be represented by additional events rather than rewriting the historical record.

## **6.3 Simplified ER diagram**

erDiagram  
    INSTITUTION \|\|--o{ APPLICATION : submits  
    INSTITUTION \|\|--o{ INSTITUTION\_CAMPUS : has  
    APPLICATION \|\|--o{ APPLICATION\_STAGE\_INSTANCE : progresses\_through  
    WORKFLOW\_DEFINITION \|\|--o{ WORKFLOW\_STAGE : contains  
    WORKFLOW\_STAGE \|\|--o{ WORKFLOW\_TRANSITION : defines  
    APPLICATION \|\|--o{ DEFICIENCY\_NOTICE : receives  
    DEFICIENCY\_NOTICE \|\|--o{ DEFICIENCY\_ITEM : contains  
    APPLICATION \|\|--o{ DOCUMENT : references  
    DOCUMENT \|\|--o{ DOCUMENT\_VERSION : versions  
    DOCUMENT\_VERSION \|\|--o{ DOCUMENT\_EXTRACTION : processed\_by  
    APPLICATION \|\|--o{ EVC\_VISIT : may\_require  
    EVC\_VISIT \|\|--o{ EVC\_COMMITTEE\_MEMBER : selects  
    EXPERT\_PROFILE \|\|--o{ EXPERT\_AVAILABILITY : provides  
    EVC\_VISIT \|\|--o{ SLOT\_RECOMMENDATION : proposes  
    EVC\_VISIT \|\|--o{ EVC\_OBSERVATION : records  
    EVC\_VISIT \|\|--o{ EVC\_REPORT : produces  
    EVC\_REPORT \|\|--o{ MEETING\_RECORD\_VERSION : versions  
    APPLICATION \|\|--o{ COMPLIANCE\_CONDITION : creates  
    COMPLIANCE\_CONDITION \|\|--o{ EVIDENCE\_SUBMISSION : receives  
    EVIDENCE\_SUBMISSION \|\|--o{ COMPLIANCE\_VERIFICATION : reviewed\_by  
    DOCUMENT \|\|--o{ DOCUMENT\_RENEWAL\_CASE : renews  
    NOTIFICATION \|\|--o{ NOTIFICATION\_ATTEMPT : attempts  
    USER \|\|--o{ USER\_ROLE\_ASSIGNMENT : receives  
    ROLE \|\|--o{ USER\_ROLE\_ASSIGNMENT : assigned  
    AUDIT\_EVENT \|\|--o{ AUDIT\_ANCHOR : anchored

The diagram is conceptual. The implementation schema must include all foreign keys, status constraints, and access checks defined in this PRD.

---

# **7\. Detailed Functional Requirements and Business Logic**

## **7.1 Module M1: Workflow Automation Engine**

### **Functional requirements**

| ID | Requirement | Priority |
| ----- | ----- | ----- |
| WF-01 | Resolve the correct workflow based on application type, institution context, and approved rule version | Must |
| WF-02 | Support multiple prescribed routes, including Only Scrutiny and routes containing EVC or other required stages | Must |
| WF-03 | Automatically advance a case only when all configured transition guards pass | Must |
| WF-04 | Require authorised roles for manual transitions and deficiency returns | Must |
| WF-05 | Require reasons for deficiency returns and other controlled reversals | Must |
| WF-06 | Preserve stage history and responsible actors | Must |
| WF-07 | Show stage age, due date, pending action, and next responsible role | Must |
| WF-08 | Support versioned workflow rules and approved effective dates | Must |
| WF-09 | Prevent duplicate transitions caused by retries or repeated requests | Must |
| WF-10 | Support controlled cancellation, reopening, or migration of in-progress cases | Should |

### **Application status model**

Recommended high-level statuses:

* `DRAFT`  
* `SUBMITTED`  
* `IN_REVIEW`  
* `RETURNED_FOR_DEFICIENCY`  
* `RESUBMITTED`  
* `AWAITING_EVC`  
* `AWAITING_COMMITTEE_ACTION`  
* `AWAITING_COMPLIANCE`  
* `DECISION_PENDING`  
* `APPROVED`  
* `REJECTED`  
* `WITHDRAWN`  
* `CLOSED`

These are suggested system states, not a substitute for official AICTE status terminology. Map them to approved statuses during requirements validation.

### **Stage instance statuses**

* `NOT_STARTED`  
* `READY`  
* `ASSIGNED`  
* `IN_PROGRESS`  
* `BLOCKED`  
* `RETURNED`  
* `COMPLETED`  
* `CANCELLED`

### **Transition algorithm**

When a transition is requested:

1. Authenticate the actor.  
2. Verify the actor's role and scope.  
3. Lock or version-check the application and active stage.  
4. Load the application’s applicable workflow version.  
5. Confirm that the requested transition exists in the workflow.  
6. Evaluate required conditions, including completion of prior actions and any mandatory EVC or verification status.  
7. If the transition is a return, validate the reason and required deficiency details.  
8. Record the transition and stage history.  
9. Update the current stage and responsible assignment.  
10. Schedule permitted notifications and background work.  
11. Commit all database changes in one transaction.  
12. Emit an audit event.

If a condition fails, the system must return a clear error and leave the workflow unchanged.

### **Deficiency return and resubmission**

1. Authorised reviewer opens the application.  
2. Reviewer records one or more deficiency items with descriptions and relevant criteria/documents.  
3. Reviewer issues the notice with a reason and response deadline where applicable.  
4. The institution receives a notification.  
5. The institution submits a new application submission or required document versions.  
6. The platform records the submission and links it to the notice.  
7. The case returns to the configured review stage.  
8. The reviewer resolves each deficiency item or returns it again with a reason.  
9. The case advances only when the required conditions are satisfied.

A new submission must not erase the previous submission or the original deficiency notice.

## **7.2 Module M2: Role-Based Dashboards**

### **Dashboard requirements**

* Aggregate counts by region, stage, institution, application type, officer, and committee.  
* Display pending, overdue, completed, and blocked work.  
* Calculate application ageing and time remaining to the applicable deadline.  
* Show workload by assigned officer and identify queues with growing backlogs.  
* Display EVC scheduling and report status.  
* Display outstanding undertakings and document renewals.  
* Provide drill-down to authorised case records.  
* Link to the eight consolidated report categories.  
* Display data freshness and integration delays.  
* Apply the same definitions and permissions as the underlying records.

### **Metric definitions**

| Metric | Definition |
| ----- | ----- |
| Application age | Current time minus application submission time, unless an approved reporting rule specifies a different start point |
| Stage age | Current time minus the stage entry time for an active stage |
| Time remaining | Applicable due time minus current time |
| Overdue duration | Current time minus due time when the due time has passed |
| Stage pendency | Count of active cases whose current stage is the specified stage |
| EVC scheduling lead time | Confirmed EVC start time minus the date the EVC became ready for scheduling |
| Evidence verification time | Verification completion time minus evidence submission time |
| Notification delivery rate | Delivered notifications divided by notifications for which a delivery outcome is available, with the reporting denominator clearly stated |
| Case closure duration | Closure time minus the configured case start time |

Business owners must approve the official definitions before dashboards are used for performance assessment.

## **7.3 Module M3: EVC Scheduling and Management**

### **Core requirements**

* Maintain the EVC queue.  
* Track applications requiring an EVC.  
* Record committee assignments and selected experts.  
* Track proposed, confirmed, postponed, completed, and cancelled visits.  
* Maintain calendar entries, invitations, reminders, completion deadlines, and escalations.  
* Track outstanding committee inputs and reports.

The following enhanced workflow is the second principal innovation.

### **EVC Committee Coordination and Meeting-to-Record Assistant**

#### **Step 1: EVC readiness**

When the application reaches the configured stage requiring an EVC, the workflow engine creates or activates the EVC work item.

The system records:

* The application and institution.  
* The applicable EVC deadline.  
* The required committee composition.  
* The expected visit duration.  
* Any mandatory visit constraints.  
* The authorised coordinator.

#### **Step 2: Authorised expert selection**

The authorised regional officer or designated authority selects the required 4–5 experts.

The backend must verify that:

* The actor has permission to assign the EVC committee.  
* Each selected expert has a valid expert profile and applicable eligibility status.  
* No selected expert is duplicated in the same committee.  
* Any applicable committee composition rules are satisfied.  
* The committee size matches the configured rule.

A change to the committee after selection requires an authorised action and recorded reason.

#### **Step 3: Availability collection**

The system obtains availability through:

1. An approved calendar connection, if available and authorised.  
2. Availability submitted or confirmed by each selected expert.  
3. Institution availability entered or confirmed by an authorised institutional contact.

Each availability record should contain its time interval, source, last confirmation time, and status.

The system must account for stale availability. If a participant's calendar or availability data is too old under the configured freshness policy, the slot must be marked unconfirmed or revalidation must be requested.

#### **Step 4: Candidate slot generation**

The scheduler generates candidate intervals within the allowed scheduling horizon.

For every candidate, it evaluates:

* Availability of every active selected expert.  
* Institution availability.  
* Required meeting duration.  
* Existing confirmed calendar events.  
* Mandatory time or location constraints.  
* Prescribed deadline.  
* Any approved preparation lead time.

A candidate is feasible only if all mandatory constraints pass.

#### **Step 5: Candidate ranking and explanation**

Feasible candidates may be ranked using configurable criteria, such as:

* Earliest feasible completion within the deadline.  
* Availability confidence and freshness.  
* Avoidance of known conflicts.  
* Adequate preparation time.  
* Reduced rescheduling risk.

The system should explain why a candidate ranks higher than another. It must not hide mandatory constraints behind a score.

Example explanation:

> Recommended: all five selected experts and the institution are available; no known calendar conflicts exist; the slot is within the required EVC deadline; and availability was confirmed recently.

#### **Step 6: No feasible slot**

If no feasible slot exists:

* Store the failed scheduling attempt.  
* Identify the blocking participants or constraints.  
* Show the nearest alternative dates where possible.  
* Flag deadline risk.  
* Notify the authorised coordinator or regional officer.  
* Create an escalation event according to the configured rule.

The system must not automatically replace an expert or select a conflicting time.

#### **Step 7: Confirm the schedule**

When the officer selects a recommended slot:

1. Recheck all selected experts' availability.  
2. Recheck institution availability.  
3. Verify the slot has not been booked or blocked since recommendation.  
4. Verify the deadline and committee assignment remain valid.  
5. Reserve the slot in the platform database within a transaction.  
6. Create the confirmed EVC event.  
7. Queue invitations and reminders.  
8. Record the confirmation in the audit trail.

If a conflict is detected during confirmation, return a conflict response and ask the officer to choose another slot.

#### **Step 8: Visit completion**

The platform tracks:

* Visit confirmed.  
* Invitations sent.  
* Required participants acknowledged, where supported.  
* Visit completed or postponed.  
* Outstanding observations or committee inputs.  
* EVC report draft status.  
* Final report approval.

#### **Step 9: Meeting-to-Record Assistant**

The assistant generates draft:

* Minutes of Meeting.  
* Criterion-wise observations.  
* Follow-up questions or unresolved issues.  
* Action items.  
* EVC report sections based on the applicable template.

Each draft must be based on authorised committee notes, structured forms, and permitted transcripts. Missing or conflicting inputs must be flagged. The assistant must not invent observations or make a statutory determination.

A committee member or authorised officer must review and approve the final record. The approved version is immutable; corrections create a new version with an explanation.

## **7.4 Module M4: Undertaking and Compliance Tracker**

### **Requirements**

* Create compliance conditions from an approved application or decision record.  
* Record due date, condition description, evidence requirements, responsible institution, and verification authority.  
* Send reminders before deadlines and escalations after missed deadlines.  
* Accept evidence submissions and link document versions.  
* Support clarification requests and multiple submissions.  
* Require authorised verification before marking a condition fulfilled.  
* Preserve the verification history and closure reason.

### **Condition status model**

* `OPEN`  
* `EVIDENCE_SUBMITTED`  
* `UNDER_REVIEW`  
* `CLARIFICATION_REQUIRED`  
* `VERIFIED_COMPLIANT`  
* `VERIFIED_NON_COMPLIANT`  
* `OVERDUE`  
* `CLOSED`  
* `REOPENED`

`OVERDUE` can be represented as a derived flag rather than the primary state. The design should avoid losing the underlying status when a due date passes.

### **Evidence verification flow**

1. Condition is created with its due date and evidence requirements.  
2. Reminder jobs are scheduled.  
3. Institution uploads evidence.  
4. System creates an evidence submission and links the file versions.  
5. Compliance officer reviews the submission.  
6. Officer verifies it, requests clarification, or records a negative result with reasons.  
7. If clarification is requested, the institution submits a new version or response.  
8. The system closes the condition only when the configured approval criteria are met.  
9. Audit and reporting records are updated.

## **7.5 Module M5: Document Expiry and Renewal Alerts**

### **Requirements**

* Store document type, issuer, reference, issue date, expiry date where applicable, version, and verification status.  
* Link documents to institutions, campuses, applications, or compliance conditions as appropriate.  
* Apply configurable expiry rules.  
* Generate advance reminders and overdue escalations.  
* Track renewal submissions and verification.  
* Preserve previous versions and their validity periods.  
* Flag missing or inconsistent metadata.  
* Restrict document access by role and scope.

### **Expiry calculation**

For a document with a valid expiry date:

* `days_remaining = expiry_date - current_date` using the applicable policy timezone.  
* An advance alert is generated when `days_remaining` matches a configured reminder threshold.  
* An overdue event is generated when the expiry date has passed and the document has not been replaced or accepted under the applicable rule.

The product must not assume all document types use the same reminder thresholds. Renewal can be considered complete only when the required new version has passed the configured review or verification process.

---

# **8\. Notification, Escalation, and Background Job Design**

## **8.1 Notification lifecycle**

Recommended statuses:

* `QUEUED`  
* `PROCESSING`  
* `SENT`  
* `DELIVERED`  
* `FAILED`  
* `RETRY_PENDING`  
* `CANCELLED`  
* `UNKNOWN`

`SENT` means the provider accepted the send request. `DELIVERED` should be used only when delivery evidence is available. If the provider cannot confirm delivery, retain an appropriate status rather than claiming success.

## **8.2 Notification processing flow**

1. A business event occurs.  
2. The backend creates an outbox event in the same transaction as the business change.  
3. A background worker reads the event.  
4. The notification rule resolves the recipient, channel, and template.  
5. The worker creates a notification record.  
6. The channel adapter attempts delivery.  
7. The result is recorded as a delivery attempt.  
8. Failed attempts are retried according to the configured retry policy.  
9. Permanent failures create an operational alert or escalation.  
10. Reporting reads the notification and attempt history.

The transactional outbox pattern prevents a case transition from being committed while its notification event is silently lost.

## **8.3 Escalation logic**

An escalation rule should specify:

* Triggering event or entity type.  
* Deadline or overdue threshold.  
* Recipient role and scope.  
* Notification channel.  
* Repeat interval, if any.  
* Maximum escalation level.  
* Resolution conditions.  
* Whether the escalation is informational or requires an action.

Duplicate escalations must be prevented for the same event and threshold window.

## **8.4 Background jobs**

| Job | Trigger | Failure handling |
| ----- | ----- | ----- |
| Deadline scanner | Scheduled interval | Retry and alert if repeated failure |
| Document expiry scanner | Daily or configured interval | Record missed scan window and recover |
| Notification delivery | Event-driven | Retry with bounded backoff |
| OCR processing | New document version | Mark failed and permit authorised reprocessing |
| Calendar sync | Scheduled or event-driven | Record sync timestamp and stale-data warning |
| Slot recommendation | Officer requests scheduling | Store calculation version and availability snapshot |
| Report generation | User request or schedule | Retry, expose status, and expire download links |
| Audit anchoring | Scheduled batch or event threshold | Queue for retry; core workflow continues |
| Integration sync | Configured schedule | Idempotent retry and error reporting |

---

# **9\. Detailed API Specification**

The following are **proposed internal APIs** for the new platform. They are not claims about existing AICTE API endpoints. Exact external integrations must be confirmed separately.

## **9.1 API conventions**

Base path:

`/api/v1`

Format: JSON over HTTPS, except file uploads and downloads.

Authentication: Bearer token from the configured identity provider.

Common headers:

* `Authorization: Bearer <token>`  
* `Content-Type: application/json`  
* `Idempotency-Key: <unique-request-key>` for operations where retries could create duplicates  
* `If-Match: <record-version>` for selected update operations using optimistic concurrency

Common response fields where appropriate:

* `id`  
* `status`  
* `created_at`  
* `updated_at`  
* `version`

### **Pagination**

Use cursor-based pagination for large lists:

`GET /api/v1/applications?limit=50&cursor=...&status=IN_REVIEW`

Responses should include:

{  
  "data": \[\],  
  "page": {  
    "limit": 50,  
    "next\_cursor": null  
  }  
}

### **Error format**

{  
  "error": {  
    "code": "EVC\_SLOT\_CONFLICT",  
    "message": "The selected slot is no longer available.",  
    "details": {  
      "evc\_visit\_id": "uuid",  
      "conflicting\_resource": "selected\_expert"  
    },  
    "correlation\_id": "uuid"  
  }  
}

Expected status codes:

| Code | Use |
| ----- | ----- |
| 200 | Successful read or update |
| 201 | Resource created |
| 202 | Accepted for asynchronous processing |
| 204 | Successful operation with no response body |
| 400 | Invalid request |
| 401 | Unauthenticated |
| 403 | Authenticated but not authorised |
| 404 | Resource not found or not visible to the caller |
| 409 | State conflict, duplicate operation, or scheduling conflict |
| 412 | Optimistic concurrency/version mismatch |
| 422 | Business rule validation failure |
| 429 | Rate limit exceeded |
| 500 | Unexpected server error |
| 503 | Temporarily unavailable dependency |

The backend must not expose restricted records through different error messages that reveal whether a resource exists outside the user's scope.

## **9.2 API inventory**

### **Identity and user scope**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/me` | Current user profile and authorised scopes |
| GET | `/me/permissions` | Effective permissions |
| GET | `/users` | Search users within permitted scope |
| POST | `/users/{id}/role-assignments` | Grant a scoped role, subject to permission |
| PATCH | `/users/{id}/role-assignments/{assignmentId}` | Change or revoke role assignment |

### **Institutions and profiles**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/institutions` | Search authorised institution records |
| POST | `/institutions` | Create institution record, if permitted |
| GET | `/institutions/{id}` | Read institution profile |
| PATCH | `/institutions/{id}` | Update permitted fields |
| GET | `/institutions/{id}/campuses` | List campuses |
| POST | `/institutions/{id}/campuses` | Add campus |
| GET | `/institutions/{id}/documents` | List authorised document records |
| GET | `/institutions/{id}/applications` | List applications for the institution |

### **Applications and workflow**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| POST | `/applications` | Create a draft application |
| GET | `/applications` | Search authorised applications |
| GET | `/applications/{id}` | Retrieve case summary |
| PATCH | `/applications/{id}` | Update permitted draft fields |
| POST | `/applications/{id}/submit` | Submit application |
| GET | `/applications/{id}/workflow` | Read workflow path and current stage |
| GET | `/applications/{id}/history` | Read authorised case history |
| POST | `/applications/{id}/transitions` | Request a permitted transition |
| POST | `/applications/{id}/assignments` | Assign case or task |
| POST | `/applications/{id}/deficiency-notices` | Issue authorised deficiency notice |
| POST | `/deficiency-notices/{id}/responses` | Submit institutional response |
| POST | `/deficiency-items/{id}/resolve` | Record authorised resolution |

### **Documents and OCR**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| POST | `/documents/upload-sessions` | Obtain a controlled upload session |
| POST | `/documents` | Register document metadata |
| GET | `/documents/{id}` | Retrieve document metadata |
| GET | `/documents/{id}/versions` | List document versions |
| POST | `/documents/{id}/versions` | Add a new version |
| POST | `/document-versions/{id}/ocr-checks` | Queue OCR and validation |
| GET | `/document-versions/{id}/checks` | Read OCR and validation outcomes |
| POST | `/document-check-results/{id}/review` | Record authorised review |
| POST | `/document-renewal-cases` | Open a renewal case |

### **EVC and scheduling**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/evc-visits` | Search EVC queue |
| POST | `/applications/{id}/evc-visits` | Create an EVC work item if required |
| GET | `/evc-visits/{id}` | Read visit details |
| PUT | `/evc-visits/{id}/committee-members` | Record authorised committee selection |
| POST | `/evc-visits/{id}/availability-requests` | Request availability from selected experts |
| POST | `/experts/{id}/availability` | Submit availability |
| GET | `/experts/{id}/availability` | Read permitted availability |
| POST | `/evc-visits/{id}/slot-recommendations` | Generate feasible slot recommendations |
| GET | `/evc-visits/{id}/slot-recommendations` | List recommendations |
| POST | `/evc-visits/{id}/confirm-schedule` | Confirm a recommended slot |
| POST | `/evc-visits/{id}/reschedule` | Request authorised rescheduling |
| POST | `/evc-visits/{id}/postpone` | Record postponement |
| POST | `/evc-visits/{id}/complete` | Record visit completion |
| GET | `/evc-visits/{id}/events` | Read visit history |
| POST | `/evc-visits/{id}/invitations` | Send or resend invitations |

### **EVC reports and meeting records**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| POST | `/evc-visits/{id}/observations` | Record authorised observations |
| POST | `/evc-visits/{id}/meeting-record-drafts` | Generate a draft from authorised inputs |
| GET | `/meeting-records/{id}` | Read draft or approved record |
| PATCH | `/meeting-records/{id}` | Edit draft, subject to permissions |
| POST | `/meeting-records/{id}/submit-review` | Submit draft for committee review |
| POST | `/meeting-records/{id}/approve` | Approve a record |
| POST | `/meeting-records/{id}/request-changes` | Return draft with review comments |
| GET | `/meeting-records/{id}/sources` | Inspect source references where permitted |

### **Undertakings and evidence**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/compliance-conditions` | Search conditions |
| POST | `/applications/{id}/compliance-conditions` | Create a condition |
| GET | `/compliance-conditions/{id}` | Read condition |
| POST | `/compliance-conditions/{id}/evidence-submissions` | Submit evidence |
| GET | `/evidence-submissions/{id}` | Read submission |
| POST | `/evidence-submissions/{id}/verification` | Record authorised verification |
| POST | `/compliance-conditions/{id}/close` | Close condition where permitted |
| POST | `/compliance-conditions/{id}/reopen` | Reopen with reason and authorisation |

### **Notifications and escalations**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/notifications` | List notifications in scope |
| GET | `/notifications/{id}` | Read notification status |
| POST | `/notifications/{id}/retry` | Retry failed delivery if permitted |
| GET | `/notifications/{id}/attempts` | Read delivery attempts |
| GET | `/escalations` | Search active and historical escalations |
| POST | `/escalations/{id}/resolve` | Record authorised resolution |

### **Reports and audit**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/reports` | List available report definitions |
| POST | `/report-runs` | Generate report |
| GET | `/report-runs/{id}` | Read report status |
| GET | `/report-runs/{id}/download` | Download authorised output |
| GET | `/audit-events` | Search authorised audit records |
| GET | `/audit-events/{id}` | Read audit event |
| POST | `/audit-verifications` | Verify a record fingerprint |
| GET | `/audit-anchors` | Read authorised ledger anchoring status |

### **Configuration and integrations**

| Method | Endpoint | Purpose |
| ----- | ----- | ----- |
| GET | `/admin/workflow-definitions` | List configured workflows |
| POST | `/admin/workflow-definitions` | Create a draft workflow definition |
| POST | `/admin/workflow-definitions/{id}/validate` | Validate workflow configuration |
| POST | `/admin/workflow-definitions/{id}/publish` | Publish an approved version |
| GET | `/admin/notification-rules` | List notification rules |
| POST | `/admin/notification-rules` | Create or update a draft rule |
| GET | `/admin/escalation-rules` | List escalation rules |
| POST | `/admin/escalation-rules` | Create or update a draft rule |
| GET | `/admin/integrations` | List approved integration configurations |
| POST | `/admin/integrations/{id}/test` | Test authorised integration connectivity |
| GET | `/admin/jobs` | Read job status and failures |

All endpoints require server-side authorisation, input validation, rate limiting where appropriate, and audit logging for sensitive actions.

## **9.3 Example: create application**

Request:

{  
  "institution\_id": "7a1b0000-0000-4000-8000-000000000001",  
  "campus\_id": "7a1b0000-0000-4000-8000-000000000002",  
  "application\_type\_code": "NEW\_INSTITUTION",  
  "requested\_academic\_year": "2027-28"  
}

Response:

{  
  "id": "7a1b0000-0000-4000-8000-000000000003",  
  "application\_number": "DRAFT-2027-000123",  
  "status": "DRAFT",  
  "version": 1,  
  "created\_at": "2026-10-26T09:00:00Z"  
}

The example values are illustrative. Production application numbers must follow the approved numbering scheme.

## **9.4 Example: select EVC committee members**

Request:

{  
  "members": \[  
    {  
      "expert\_user\_id": "expert-uuid-1",  
      "committee\_role": "MEMBER"  
    },  
    {  
      "expert\_user\_id": "expert-uuid-2",  
      "committee\_role": "MEMBER"  
    },  
    {  
      "expert\_user\_id": "expert-uuid-3",  
      "committee\_role": "MEMBER"  
    },  
    {  
      "expert\_user\_id": "expert-uuid-4",  
      "committee\_role": "MEMBER"  
    },  
    {  
      "expert\_user\_id": "expert-uuid-5",  
      "committee\_role": "MEMBER"  
    }  
  \],  
  "selection\_reason": "Committee selected by the authorised regional officer"  
}

The backend must validate the actor's authority, selected members' eligibility, duplicate membership, and configured committee composition. The API must not silently replace any member.

## **9.5 Example: request slot recommendations**

Request:

{  
  "search\_window": {  
    "start\_at": "2026-11-01T00:00:00+05:30",  
    "end\_at": "2026-11-20T23:59:59+05:30"  
  },  
  "duration\_minutes": 180,  
  "deadline\_at": "2026-11-18T17:00:00+05:30",  
  "require\_fresh\_availability": true  
}

Response:

{  
  "evc\_visit\_id": "evc-uuid-1",  
  "recommendations": \[  
    {  
      "id": "slot-uuid-1",  
      "start\_at": "2026-11-10T10:00:00+05:30",  
      "end\_at": "2026-11-10T13:00:00+05:30",  
      "feasible": true,  
      "rank": 1,  
      "explanation": \[  
        "All selected experts are available",  
        "Institution availability is confirmed",  
        "No known calendar conflicts exist",  
        "The slot is within the prescribed deadline"  
      \],  
      "availability\_snapshot\_at": "2026-10-26T09:30:00Z",  
      "expires\_at": "2026-10-26T09:45:00Z"  
    }  
  \]  
}

The API must not return a feasible slot unless the system has checked all mandatory participants and constraints. The recommendation expires or must be revalidated before confirmation.

## **9.6 Example: confirm a slot**

Request:

{  
  "slot\_recommendation\_id": "slot-uuid-1",  
  "expected\_evc\_version": 4,  
  "confirmation\_note": "Confirmed by authorised regional officer"  
}

The backend must recheck availability, deadline, committee membership, and booking conflicts in a transaction before confirming the meeting.

If a conflict has appeared since recommendation, return `409 EVC_SLOT_CONFLICT`. The visit must remain unconfirmed.

## **9.7 Example: generate an EVC draft report**

Request:

{  
  "record\_type": "EVC\_REPORT",  
  "template\_version": "approved-template-v1",  
  "source\_references": \[  
    {  
      "source\_type": "COMMITTEE\_NOTE",  
      "source\_id": "note-uuid-1"  
    },  
    {  
      "source\_type": "OBSERVATION",  
      "source\_id": "observation-uuid-1"  
    }  
  \],  
  "transcript\_reference": null  
}

Response:

{  
  "meeting\_record\_id": "record-uuid-1",  
  "status": "DRAFT",  
  "requires\_human\_approval": true,  
  "warnings": \[  
    "One criterion has no supporting observation and requires committee review"  
  \]  
}

The system must not turn a draft into an approved report automatically.

---

# **10\. API Business Rules and Transaction Safety**

## **10.1 Idempotency**

For operations that may be retried, the backend should accept an idempotency key and store the result associated with that key.

Examples:

* Application submission.  
* EVC confirmation.  
* Notification dispatch event.  
* Evidence submission.  
* Report generation request.

A repeated request with the same key must not create duplicate business records.

## **10.2 Optimistic concurrency**

Editable records should carry a version number or equivalent concurrency token.

If a user attempts to update a record based on an outdated version, return `412 Precondition Failed` or an equivalent conflict response.

## **10.3 Scheduling race conditions**

Two coordinators might attempt to book the same expert for overlapping times. Prevent this using:

* Database transactions.  
* Revalidation immediately before confirmation.  
* An appropriate database constraint or locking strategy for confirmed intervals.  
* Conflict responses and an updated recommendation flow.

A recommendation is not a reservation. A confirmed schedule is created only after the final atomic validation succeeds.

## **10.4 Time zones**

* Store event timestamps in UTC.  
* Retain the intended local timezone for institution visits and deadline calculations.  
* Display EVC times in the relevant local timezone.  
* Treat daylight-saving changes correctly for any experts or services in other time zones.  
* Never compare unnormalised local timestamps from different sources.

## **10.5 External integration failures**

External calendar, email, SMS, or legacy-system failures must not silently corrupt the main workflow.

Use queued jobs, bounded retries, failure records, and operational alerts. If a calendar integration is unavailable, the system must mark availability as stale or request manual confirmation rather than claim it has verified the calendar.

---

# **11\. Consolidated Reporting Requirements**

All eight report categories are mandatory.

## **11.1 Report specification**

| Report | Core fields | Filters | Typical authorised users |
| ----- | ----- | ----- | ----- |
| Region-wise performance | Region, applications received/completed, stage-wise pendency, processing time, overdue cases, EVC completion, compliance status | Date range, region, application type, institution type | Central administration, regional leadership |
| Application pendency | Application number, institution, stage, stage age, application age, deadline, overdue duration, owner, next action | Region, stage, age band, officer, status | Regional officers, scrutiny officers, central administration |
| EVC status | Application, selected committee, proposed/confirmed date, scheduling status, deadline, conflicts, visit status, report status | Region, coordinator, date range, status | Regional officers, EVC coordinators, authorised experts |
| Undertaking compliance | Condition, due date, evidence status, verification status, overdue days, reviewer, escalation | Region, condition type, status, due period | Compliance officers, regional officers |
| Document validity | Institution, document type, issue/expiry date, version, verification status, renewal status | Document type, region, expiry window, status | Compliance officers, regional officers |
| Overdue actions | Entity type, case, action, owner, due date, overdue duration, escalation level, resolution | Region, role, action type, overdue range | Supervisors and authorised administrators |
| Notification delivery | Event, recipient category, channel, sent/delivered/failed status, attempt count, failure reason, last attempt | Date range, channel, event type, delivery status | Administrators, authorised auditors |
| Case closure | Application, closure date, final status, closure authority, reason, duration, reopen status | Region, date range, application type, closure outcome | Central administration, regional officers, auditors |

## **11.2 Reporting behaviour**

* Support CSV/Excel downloads for data analysis and PDF summaries where required.  
* Apply the same role and scope checks as the live application.  
* Record the reporting period, filters, generation timestamp, and data freshness.  
* Define whether the report reflects a live query or a point-in-time snapshot.  
* Record sensitive exports in the audit trail.  
* Avoid exporting unnecessary personal data.  
* Support scheduled generation and distribution only through authorised channels.  
* Make large report generation asynchronous and expose progress and failure state.

## **11.3 Report reconciliation**

Dashboard counts and report totals must use the same status definitions and deadline logic. Acceptance testing must compare report results against known test records to prevent discrepancies between dashboard totals and downloaded files.

---

# **12\. Business Rules Catalogue**

The following rules are global invariants. Specific thresholds and regulatory conditions must be configured and approved.

| ID | Business rule |
| ----- | ----- |
| BR-01 | An application must be associated with a valid institution and application type. |
| BR-02 | Workflow selection must use an approved applicable rule version. |
| BR-03 | A workflow transition must exist in the selected workflow and satisfy all configured guards. |
| BR-04 | Only authorised roles can issue deficiency returns, approve records, or make controlled decisions. |
| BR-05 | Deficiency returns require reasons and retain the original submission history. |
| BR-06 | An application may require an EVC only when its applicable workflow or approved rules specify it. |
| BR-07 | EVC committee members are selected by an authorised officer, not by the scheduling algorithm. |
| BR-08 | The scheduler evaluates the exact active committee membership for the EVC. |
| BR-09 | A slot cannot be confirmed unless required participants and the institution satisfy mandatory availability constraints. |
| BR-10 | Slot recommendations must be revalidated before booking. |
| BR-11 | If no feasible slot exists within the deadline, the system flags and escalates the risk; it does not silently override constraints. |
| BR-12 | Meeting-record generation produces a draft, never an automatic statutory finding or approved report. |
| BR-13 | Only authorised users can approve a final EVC record. |
| BR-14 | A compliance condition is not fulfilled solely because evidence has been uploaded. |
| BR-15 | A document renewal is not complete until the configured verification requirements are satisfied. |
| BR-16 | Document versions are immutable and retain their historical metadata. |
| BR-17 | OCR findings with uncertain confidence require review and cannot independently reject an application. |
| BR-18 | Every sensitive workflow action must create an audit event. |
| BR-19 | Notification creation and delivery are distinct states; retries are recorded. |
| BR-20 | Report downloads are restricted by the user's role and data scope. |
| BR-21 | Configuration changes are versioned, approved, and auditable. |
| BR-22 | Blockchain anchoring is optional and must not block the main workflow. |
| BR-23 | Historical applications retain their original rule-version reference unless an approved migration is performed. |
| BR-24 | Case closure follows the configured authorised process and does not erase history. |

---

# **13\. Security, Privacy, and Audit Requirements**

## **13.1 Authentication and authorisation**

* Use an approved identity provider.  
* Enforce role-based access and record-level scope.  
* Use stronger authentication for privileged actions where required.  
* Revalidate permissions on every backend request.  
* Revoke access promptly when a user or role assignment is disabled.  
* Prevent institutional users from viewing other institutions' records.

## **13.2 Data protection**

* Encrypt data in transit and at rest.  
* Keep secrets and integration credentials in a secure secret manager.  
* Scan uploaded files for malware.  
* Use short-lived, authorised download links.  
* Prevent direct public access to document storage.  
* Apply retention and deletion policies to files, transcripts, and personal information.  
* Collect only information necessary for the regulatory workflow.

## **13.3 Meeting-record protection**

* Use recordings or transcripts only where authorised.  
* Restrict access to authorised committee members and officers.  
* Record source references used to generate draft records.  
* Keep draft and approved versions separate.  
* Apply approved retention and deletion policies.  
* Do not expose confidential transcript content in ordinary audit metadata.

## **13.4 Audit requirements**

Each relevant audit event should record:

* Actor or service identity.  
* Action performed.  
* Entity type and identifier.  
* Timestamp.  
* Previous and new status where applicable.  
* Reason for controlled actions.  
* Correlation ID for tracing related operations.  
* Relevant version references.  
* Hash-chain information where used.

Avoid placing full sensitive payloads in audit logs.

## **13.5 Blockchain audit layer**

If enabled:

1. Calculate the hash of the selected record version or canonical event representation.  
2. Store the hash and minimum metadata in the permissioned ledger.  
3. Keep the source record in the protected application database or object storage.  
4. Record the ledger transaction reference in the audit service.  
5. Verify by recomputing the hash and comparing it with the anchored value.  
6. Alert authorised auditors to a mismatch.

The ledger must not be treated as proof that the source document was genuine when first uploaded. Ledger outages must not block normal case processing.

## **13.6 Backup and recovery**

Provisional targets for planning, to be confirmed with AICTE:

* Recovery Point Objective (RPO): 15 minutes.  
* Recovery Time Objective (RTO): 4 hours.  
* Encrypted backups with access restrictions.  
* Periodic restore testing.  
* Separate protection for audit records and encryption keys.  
* Documented incident and recovery procedures.

These are proposed targets, not confirmed organisational service levels.

---

# **14\. Non-Functional Requirements**

Targets below are provisional and must be validated against current workload, approved infrastructure, and security requirements.

| Category | Proposed requirement |
| ----- | ----- |
| Performance | Common read endpoints should target p95 response time below 500 ms under the agreed test workload, excluding large file transfer and long-running jobs |
| Availability | A provisional 99.5% monthly service target may be used for planning, subject to infrastructure and organisational approval |
| Scalability | Support horizontal scaling of web workers and background workers if measured demand requires it |
| File handling | Support configured file size/type limits, malware scanning, and resumable or multipart upload where appropriate |
| Accessibility | Target WCAG 2.1 AA practices for key user journeys, subject to formal validation |
| Audit completeness | 100% of designated sensitive actions should generate traceable audit events |
| Workflow integrity | No invalid transition may commit; failed transitions leave business state unchanged |
| Notification reliability | Retry failures according to configured policy and preserve attempt history |
| Data integrity | Enforce foreign keys, uniqueness, transaction integrity, and immutable document versions |
| Maintainability | Automated unit, integration, and regression tests for workflow rules |
| Observability | Monitor API latency, errors, job queues, OCR failures, calendar sync, notification delivery, and database health |
| Security | Complete threat modelling, access-control tests, dependency scanning, and security testing before production |
| Recovery | Meet approved RPO/RTO after recovery tests |
| Interoperability | Use documented versioned internal APIs and approved external interfaces |

## **14.1 Load testing**

Once current workload figures are confirmed, test realistic combinations of:

* Concurrent authenticated sessions.  
* Application search and dashboard reads.  
* Application submissions and document uploads.  
* OCR processing queues.  
* Deadline and notification bursts.  
* EVC scheduling recommendation requests.  
* Report generation.  
* Calendar and external integration delays.  
* Recovery after worker or service failure.

Do not claim that the system supports a particular institution count or request rate until tested.

---

# **15\. Data Retention and Lifecycle**

Retention periods must be set by AICTE policy, applicable regulations, records-management requirements, and security review.

| Data category | Lifecycle requirements |
| ----- | ----- |
| Applications and decisions | Preserve according to approved regulatory record-retention rules |
| Application submissions | Retain historical submissions and link them to deficiency notices and review outcomes |
| Document versions | Preserve required historical versions; restrict replacement and deletion |
| OCR output | Retain according to operational value, audit needs, and policy; preserve provenance for consequential results |
| EVC scheduling history | Retain selection, availability evidence, recommendations, confirmations, and rescheduling events according to policy |
| Draft meeting records | Retain version history according to approved records policy |
| Approved reports | Preserve as official records under the applicable retention schedule |
| Meeting recordings/transcripts | Retain only when authorised and according to explicit policy |
| Notifications | Retain delivery evidence according to audit and operational requirements |
| Audit events | Protect against unauthorised alteration and retain according to the approved audit policy |
| Temporary exports | Expire download links and remove temporary files after the configured retention window |
| Integration logs | Retain enough detail for troubleshooting and accountability without storing unnecessary sensitive payloads |

Deletion and archival processes must not break required foreign-key relationships or destroy records that must be retained for audit.

---

# **16\. Integration Requirements**

## **16.1 Existing AICTE systems**

Integration discovery must determine:

* Which systems are authoritative for institution identifiers and application records.  
* Whether approved APIs exist.  
* Whether import, export, or bidirectional synchronisation is allowed.  
* Which system owns each field.  
* How duplicate applications and updates are reconciled.  
* How authentication, data sharing, audit, and failure recovery are handled.

Until these details are confirmed, use mock connectors or controlled sample imports in the prototype.

## **16.2 Calendar integrations**

Calendar integrations must support only the permissions approved by the relevant expert and organisation.

The platform must not assume it can read all calendar details. Availability can instead be entered through a controlled platform form.

The scheduling service should store only what it needs to determine conflicts: availability intervals, source, freshness, and relevant event references. Calendar event titles and descriptions should not be collected unless necessary and authorised.

## **16.3 Email and SMS providers**

Use adapters so the application can switch providers without changing business logic.

Each adapter should report:

* Request accepted or rejected.  
* Provider message reference.  
* Delivery confirmation where available.  
* Failure category.  
* Retryability.  
* Last attempt time.

## **16.4 Document issuers and registries**

Issuer verification should be integrated only where a legitimate, approved interface exists. The system must not claim automatic verification if it merely extracted text or compared document fields.

---

# **17\. Testing Strategy and Acceptance Criteria**

## **17.1 Workflow tests**

* Every configured sample route follows the approved sequence.  
* Invalid transitions are rejected.  
* Unauthorised returns are rejected.  
* Deficiency returns require reasons.  
* Resubmissions preserve prior versions and history.  
* Rule-version changes do not silently rewrite historical cases.  
* Repeated requests do not create duplicate transitions.

## **17.2 EVC tests**

* Only authorised officers can select or replace experts.  
* The selected member list is persisted for the particular EVC.  
* Availability checks cover every selected expert and the institution.  
* Conflicting or stale availability is detected or explicitly marked uncertain.  
* Recommendations explain feasibility and deadline compliance.  
* No feasible slot results in a visible warning and escalation.  
* Confirmation rechecks availability and prevents double-booking.  
* Calendar integration failure does not falsely mark invitations or schedules as synchronised.  
* Draft meeting records remain drafts until authorised approval.  
* Missing or conflicting source inputs are flagged instead of invented.

## **17.3 Compliance and document tests**

* Evidence submission does not automatically close a condition.  
* Only authorised reviewers can verify evidence.  
* Due dates trigger configured reminders and escalations.  
* Expiry rules apply only to applicable document types.  
* New versions preserve old versions and link to the renewal case.  
* OCR mismatch results can be reviewed and resolved.  
* Low-confidence OCR output does not automatically reject an application.

## **17.4 Notification and reporting tests**

* Notification attempts and retries are recorded.  
* Delivery status matches the evidence provided by the channel.  
* Failed deliveries are visible to authorised operators.  
* All eight report types can be generated and downloaded.  
* Filters and role restrictions are enforced.  
* Report totals reconcile with underlying test records.  
* Exports contain the generation timestamp and reporting period.

## **17.5 Security and audit tests**

* Cross-institution access is denied unless explicitly authorised.  
* Privileged actions are denied without permission.  
* File downloads enforce access control.  
* Sensitive actions generate audit events.  
* Audit integrity verification detects changes to anchored content.  
* Secrets do not appear in logs or API responses.  
* Backup restoration is tested.  
* File uploads are checked for type, size, and malware according to policy.

---

# **18\. Implementation Plan**

## **Phase 1: SIH Prototype — approximately 6–8 weeks**

### **Deliverables**

* Authentication and role-based access.  
* Institution profile.  
* Application intake and configurable sample workflow.  
* Stage transition validation and deficiency returns.  
* Basic document registry and OCR checks.  
* EVC queue and committee assignment records.  
* Committee-specific availability matching and slot recommendations.  
* Calendar confirmation and invitation flow using a mock or approved integration.  
* Draft EVC meeting-record generation with human approval.  
* Undertaking and document-expiry tracking.  
* Notification and escalation framework.  
* Eight downloadable report types.  
* Append-only audit trail and optional blockchain demonstration.  
* Seed data, test cases, and a cohesive demonstration journey.

## **Phase 2: Controlled Pilot — approximately 3–6 months, subject to approvals**

* Confirm APH mappings with authorised policy owners.  
* Validate the institutional data model and report definitions.  
* Integrate approved identity, portal, calendar, and notification systems.  
* Test OCR against human-verified samples.  
* Pilot with a limited authorised user group.  
* Test load, security, backup, recovery, and support procedures.  
* Measure real-world performance and user adoption.

## **Phase 3: Staged Rollout**

* Expand the configured workflows and participating institutions.  
* Add approved integrations and operational monitoring.  
* Establish training, support, and service management.  
* Review rule changes and publish new approved workflow versions.  
* Evaluate production blockchain governance and operating costs.  
* Continue security, reliability, and performance testing.

The timeline is indicative and depends on approved interfaces, requirements validation, procurement, and stakeholder availability.

---

# **19\. Risks and Mitigations**

| Risk | Impact | Mitigation |
| ----- | ----- | ----- |
| Incorrect APH mapping | Wrong routing or deadlines | Authorised rule review, versioning, effective dates, regression tests |
| Incorrect permissions | Confidential data exposure | Scope-based access, backend checks, security testing |
| OCR errors | False document flags | Confidence thresholds, human review, source visibility |
| Forged documents | Invalid evidence accepted | Approved verification processes; do not rely on OCR or hashes alone |
| No common EVC slot | Deadline missed | Explain blockers, flag risk, escalate to authorised officer |
| Stale calendar availability | False scheduling recommendation | Freshness rules and revalidation before confirmation |
| Expert replacement without authority | Invalid committee composition | Backend permission checks and recorded replacement reason |
| Generated report errors | Incorrect official record | Source-linked drafts, review, mandatory approval |
| Notification failures | Missed action | Retry logic, delivery tracking, operational alerts |
| Legacy integration delay | Delayed rollout | Early discovery, mocks, controlled fallback imports |
| Blockchain complexity | Cost and operational burden | Keep optional; validate the cross-organisation trust requirement |
| Low adoption | Incomplete or inconsistent records | User testing, training, feedback, support |
| Poor data quality | Incorrect reports and checks | Validation, source metadata, reconciliation, manual review |

---

# **20\. SIH Demonstration Scenario**

The prototype should demonstrate one end-to-end case:

1. An authorised institutional representative opens an application.  
2. The system associates it with an institution profile and checks required document metadata.  
3. OCR flags a mismatched document type or inconsistent lease expiry date.  
4. The workflow engine routes the application to the prescribed scrutiny stage.  
5. An authorised officer returns the case with a recorded deficiency reason.  
6. The institution submits corrected information, creating a new version.  
7. The EVC queue identifies that an EVC is required.  
8. The authorised regional officer selects the required 4–5 experts.  
9. The system checks the availability of those exact experts and the institution.  
10. The scheduler identifies conflicting dates, recommends feasible alternatives, and explains why the preferred slot works.  
11. The officer confirms the slot; the system records the meeting and issues invitations.  
12. After the sample visit, the assistant creates draft minutes, criterion-wise observations, action items, and an EVC report from authorised sample inputs.  
13. A committee reviewer edits and approves the report.  
14. An undertaking is created, evidence is submitted, and an authorised officer verifies it.  
15. A document approaching expiry triggers a renewal alert.  
16. A deadline is missed in the test scenario, triggering an escalation and notification-delivery record.  
17. Dashboards show pendency, EVC status, compliance, overdue actions, and closure.  
18. The reporting area generates all eight downloadable report categories.  
19. The audit screen shows actor, action, timestamp, and associated record history.  
20. If the optional ledger is enabled, the demonstration compares a stored fingerprint with a modified sample record and displays the mismatch.

---

# **21\. Open Decisions for AICTE**

These items must be resolved before production implementation.

| Decision | Why it matters |
| ----- | ----- |
| Applicable APH version and official workflow rules | Determines valid stages, deadlines, conditions, and routing |
| Official application categories and identifiers | Defines data validation and integration |
| Exact committee composition rules | Determines permissible EVC member selection |
| Required scheduling deadline and time zone | Determines slot feasibility and escalations |
| Expert availability method | Determines calendar integration versus manual confirmation |
| Authorised calendar and meeting providers | Determines invitations and calendar synchronisation |
| Official scrutiny and EVC report templates | Determines structured forms and generated drafts |
| Authorised sign-off rules | Determines who can approve reports and decisions |
| Document requirements and expiry rules | Determines registry and renewal configuration |
| Notification channels and templates | Determines delivery integrations and audit evidence |
| Report definitions and performance metrics | Ensures reports match official interpretations |
| Existing AICTE APIs and system ownership | Determines integration architecture and data reconciliation |
| Hosting and identity requirements | Determines deployment and access design |
| Records retention and transcript policy | Determines storage, access, and deletion behaviour |
| Blockchain governance requirement | Determines whether a permissioned ledger provides sufficient value |
| Current workload and service-level expectations | Determines capacity planning and performance targets |

---

# **22\. Final Product Definition**

The product is a secure, configurable regulatory workflow platform built around five core modules:

1. Workflow Automation Engine.  
2. Role-Based Dashboards.  
3. EVC Scheduling and Management.  
4. Undertaking and Compliance Tracker.  
5. Document Expiry and Renewal Alerts.

Shared supporting capabilities include institutional profiles, OCR-assisted document checks, notifications, reporting, integrations, and audit.

The two principal innovations are:

1. **Blockchain-Backed Tamper-Evident Audit Trail**, optional and limited to hashes and minimum metadata.  
2. **EVC Committee Coordination and Meeting-to-Record Assistant**, where an authorised officer selects the required 4–5 experts, the system checks the availability of those exact experts and the institution, recommends explainable non-conflicting slots within the prescribed deadline, manages the confirmed meeting, and prepares draft EVC records for human review and approval.

The platform's governing principle is that automation improves coordination, traceability, and administrative efficiency while authorised officers and committees retain control over expert selection, statutory scrutiny, verification, inspection findings, and approval decisions.

