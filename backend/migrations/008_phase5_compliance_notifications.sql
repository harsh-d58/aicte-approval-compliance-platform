-- Phase 5 Migration: Compliance and Communications Table Grants and RLS Policies
-- Grants appropriate permissions to aicte_api_writer and aicte_api_reader

GRANT SELECT, INSERT, UPDATE, DELETE ON
    public.compliance_conditions,
    public.compliance_verifications,
    public.evidence_submissions,
    public.evidence_submission_files,
    public.notifications,
    public.notification_attempts,
    public.notification_rules,
    public.escalation_rules,
    public.escalation_events
TO aicte_api_writer;

GRANT SELECT ON
    public.compliance_conditions,
    public.compliance_verifications,
    public.evidence_submissions,
    public.evidence_submission_files,
    public.notifications,
    public.notification_attempts,
    public.notification_rules,
    public.escalation_rules,
    public.escalation_events
TO aicte_api_reader;

-- RLS Policies for aicte_api_writer

CREATE POLICY aicte_api_writer_all_compliance_conditions ON public.compliance_conditions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_compliance_verifications ON public.compliance_verifications
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_evidence_submissions ON public.evidence_submissions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_evidence_submission_files ON public.evidence_submission_files
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_notifications ON public.notifications
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_notification_attempts ON public.notification_attempts
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_notification_rules ON public.notification_rules
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_escalation_rules ON public.escalation_rules
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_escalation_events ON public.escalation_events
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

-- RLS Policies for aicte_api_reader

CREATE POLICY aicte_api_reader_all_compliance_conditions ON public.compliance_conditions
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_compliance_verifications ON public.compliance_verifications
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_evidence_submissions ON public.evidence_submissions
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_evidence_submission_files ON public.evidence_submission_files
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_notifications ON public.notifications
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_notification_attempts ON public.notification_attempts
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_notification_rules ON public.notification_rules
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_escalation_rules ON public.escalation_rules
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_escalation_events ON public.escalation_events
    FOR SELECT TO aicte_api_reader USING (true);
