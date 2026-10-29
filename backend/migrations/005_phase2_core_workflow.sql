-- Phase 2: Core Workflow tables grants and RLS policies for aicte_api_reader and aicte_api_writer.

-- 1. Read privileges for aicte_api_reader
GRANT SELECT ON public.institution_campuses,
    public.institution_profile_attributes,
    public.application_types,
    public.application_submissions,
    public.aph_rule_sets,
    public.aph_rule_versions,
    public.workflow_definitions,
    public.workflow_stages,
    public.workflow_transitions,
    public.application_stage_instances,
    public.stage_history,
    public.assignments,
    public.deficiency_notices,
    public.deficiency_items,
    public.approval_decisions TO aicte_api_reader;

-- 2. Read, insert, update privileges for aicte_api_writer
GRANT SELECT, INSERT, UPDATE, DELETE ON public.institution_campuses,
    public.institution_profile_attributes,
    public.application_types,
    public.application_submissions,
    public.aph_rule_sets,
    public.aph_rule_versions,
    public.workflow_definitions,
    public.workflow_stages,
    public.workflow_transitions,
    public.application_stage_instances,
    public.stage_history,
    public.assignments,
    public.deficiency_notices,
    public.deficiency_items,
    public.approval_decisions TO aicte_api_writer;

-- 3. RLS policies for aicte_api_writer (full access inside authenticated transactions)
CREATE POLICY aicte_api_writer_all_campuses ON public.institution_campuses
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_profile_attrs ON public.institution_profile_attributes
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_app_types ON public.application_types
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_submissions ON public.application_submissions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_aph_rule_sets ON public.aph_rule_sets
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_aph_rule_versions ON public.aph_rule_versions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_workflow_defs ON public.workflow_definitions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_workflow_stages ON public.workflow_stages
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_workflow_transitions ON public.workflow_transitions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_stage_instances ON public.application_stage_instances
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_stage_history ON public.stage_history
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_assignments ON public.assignments
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_deficiency_notices ON public.deficiency_notices
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_deficiency_items ON public.deficiency_items
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_approval_decisions ON public.approval_decisions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

-- 4. RLS policies for aicte_api_reader (scoped reads)
-- Reference tables (publicly readable within API)
CREATE POLICY aicte_api_reader_select_app_types ON public.application_types
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_select_aph_rule_sets ON public.aph_rule_sets
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_select_aph_rule_versions ON public.aph_rule_versions
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_select_workflow_defs ON public.workflow_definitions
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_select_workflow_stages ON public.workflow_stages
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_select_workflow_transitions ON public.workflow_transitions
    FOR SELECT TO aicte_api_reader USING (true);

-- Institution scoped tables
CREATE POLICY aicte_api_reader_select_campuses ON public.institution_campuses
    FOR SELECT TO aicte_api_reader
    USING (api_private.can_read('institution.read', institution_id, NULL));

CREATE POLICY aicte_api_reader_select_profile_attrs ON public.institution_profile_attributes
    FOR SELECT TO aicte_api_reader
    USING (api_private.can_read('institution.read', institution_id, NULL));

-- Application scoped child tables
CREATE POLICY aicte_api_reader_select_submissions ON public.application_submissions
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.applications a
        WHERE a.id = application_id AND api_private.can_read('application.read', a.institution_id, a.id)
    ));

CREATE POLICY aicte_api_reader_select_stage_instances ON public.application_stage_instances
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.applications a
        WHERE a.id = application_id AND api_private.can_read('application.read', a.institution_id, a.id)
    ));

CREATE POLICY aicte_api_reader_select_stage_history ON public.stage_history
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.applications a
        WHERE a.id = application_id AND api_private.can_read('application.read', a.institution_id, a.id)
    ));

CREATE POLICY aicte_api_reader_select_assignments ON public.assignments
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.applications a
        WHERE a.id = application_id AND api_private.can_read('application.read', a.institution_id, a.id)
    ));

CREATE POLICY aicte_api_reader_select_deficiency_notices ON public.deficiency_notices
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.applications a
        WHERE a.id = application_id AND api_private.can_read('application.read', a.institution_id, a.id)
    ));

CREATE POLICY aicte_api_reader_select_deficiency_items ON public.deficiency_items
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.deficiency_notices dn
        JOIN public.applications a ON a.id = dn.application_id
        WHERE dn.id = deficiency_notice_id AND api_private.can_read('application.read', a.institution_id, a.id)
    ));

CREATE POLICY aicte_api_reader_select_approval_decisions ON public.approval_decisions
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.applications a
        WHERE a.id = application_id AND api_private.can_read('application.read', a.institution_id, a.id)
    ));
