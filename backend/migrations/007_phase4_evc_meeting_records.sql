-- Phase 4: EVC visits, expert selection, availability, scheduling, meeting records, grants, and RLS policies.

-- 1. Read privileges for aicte_api_reader
GRANT SELECT ON public.evc_visits,
    public.evc_committee_members,
    public.expert_profiles,
    public.expert_availability,
    public.slot_recommendations,
    public.evc_invitations,
    public.evc_visit_events,
    public.evc_observations,
    public.evc_reports,
    public.meeting_record_versions,
    public.meeting_record_sources,
    public.committee_types,
    public.committees TO aicte_api_reader;

-- 2. Read, insert, update privileges for aicte_api_writer
GRANT SELECT, INSERT, UPDATE, DELETE ON public.evc_visits,
    public.evc_committee_members,
    public.expert_profiles,
    public.expert_availability,
    public.slot_recommendations,
    public.evc_invitations,
    public.evc_visit_events,
    public.evc_observations,
    public.evc_reports,
    public.meeting_record_versions,
    public.meeting_record_sources,
    public.committee_types,
    public.committees TO aicte_api_writer;

-- 3. RLS policies for aicte_api_writer
CREATE POLICY aicte_api_writer_all_evc_visits ON public.evc_visits
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_committee_members ON public.evc_committee_members
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_expert_profiles ON public.expert_profiles
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_expert_availability ON public.expert_availability
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_slot_recommendations ON public.slot_recommendations
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_evc_invitations ON public.evc_invitations
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_evc_visit_events ON public.evc_visit_events
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_evc_observations ON public.evc_observations
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_evc_reports ON public.evc_reports
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_meeting_record_versions ON public.meeting_record_versions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_meeting_record_sources ON public.meeting_record_sources
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_committee_types ON public.committee_types
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_committees ON public.committees
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

-- 4. RLS policies for aicte_api_reader
CREATE POLICY aicte_api_reader_all_evc_visits ON public.evc_visits
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_committee_members ON public.evc_committee_members
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_expert_profiles ON public.expert_profiles
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_expert_availability ON public.expert_availability
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_slot_recommendations ON public.slot_recommendations
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_evc_invitations ON public.evc_invitations
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_evc_visit_events ON public.evc_visit_events
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_evc_observations ON public.evc_observations
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_evc_reports ON public.evc_reports
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_meeting_record_versions ON public.meeting_record_versions
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_meeting_record_sources ON public.meeting_record_sources
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_committee_types ON public.committee_types
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_committees ON public.committees
    FOR SELECT TO aicte_api_reader USING (true);
