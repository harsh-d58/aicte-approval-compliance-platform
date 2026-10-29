-- Phase 6 Migration: Reports and Dashboards Table Grants and RLS Policies
-- Grants appropriate permissions to aicte_api_writer and aicte_api_reader

GRANT SELECT, INSERT, UPDATE, DELETE ON
    public.report_definitions,
    public.report_runs,
    public.regions
TO aicte_api_writer;

GRANT SELECT ON
    public.report_definitions,
    public.report_runs,
    public.regions
TO aicte_api_reader;

-- RLS Policies for aicte_api_writer

DROP POLICY IF EXISTS aicte_api_writer_all_report_definitions ON public.report_definitions;
CREATE POLICY aicte_api_writer_all_report_definitions ON public.report_definitions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS aicte_api_writer_all_report_runs ON public.report_runs;
CREATE POLICY aicte_api_writer_all_report_runs ON public.report_runs
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS aicte_api_writer_all_regions ON public.regions;
CREATE POLICY aicte_api_writer_all_regions ON public.regions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

-- RLS Policies for aicte_api_reader

DROP POLICY IF EXISTS aicte_api_reader_all_report_definitions ON public.report_definitions;
CREATE POLICY aicte_api_reader_all_report_definitions ON public.report_definitions
    FOR SELECT TO aicte_api_reader USING (true);

DROP POLICY IF EXISTS aicte_api_reader_all_report_runs ON public.report_runs;
CREATE POLICY aicte_api_reader_all_report_runs ON public.report_runs
    FOR SELECT TO aicte_api_reader USING (true);

DROP POLICY IF EXISTS aicte_api_reader_all_regions ON public.regions;
CREATE POLICY aicte_api_reader_all_regions ON public.regions
    FOR SELECT TO aicte_api_reader USING (true);
