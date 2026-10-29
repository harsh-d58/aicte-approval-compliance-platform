-- Phase 3: Documents and OCR tables, upload sessions, grants, and RLS policies.

-- 1. Create upload_sessions table if not exists
CREATE TABLE IF NOT EXISTS public.upload_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES public.institutions(id) ON DELETE RESTRICT,
    document_type_id UUID NOT NULL REFERENCES public.document_types(id) ON DELETE RESTRICT,
    file_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    max_size_bytes BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'uploaded', 'expired', 'cancelled')),
    upload_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES public.users(id) ON DELETE RESTRICT
);

ALTER TABLE public.upload_sessions ENABLE ROW LEVEL SECURITY;

-- 2. Read privileges for aicte_api_reader
GRANT SELECT ON public.documents,
    public.document_versions,
    public.document_types,
    public.document_requirement_rules,
    public.document_extractions,
    public.document_check_results,
    public.document_renewal_cases,
    public.upload_sessions TO aicte_api_reader;

-- 3. Read, insert, update privileges for aicte_api_writer
GRANT SELECT, INSERT, UPDATE, DELETE ON public.documents,
    public.document_versions,
    public.document_types,
    public.document_requirement_rules,
    public.document_extractions,
    public.document_check_results,
    public.document_renewal_cases,
    public.upload_sessions TO aicte_api_writer;

-- 4. RLS policies for aicte_api_writer
CREATE POLICY aicte_api_writer_all_documents ON public.documents
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_doc_versions ON public.document_versions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_doc_types ON public.document_types
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_doc_rules ON public.document_requirement_rules
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_doc_extractions ON public.document_extractions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_doc_checks ON public.document_check_results
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_doc_renewals ON public.document_renewal_cases
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_upload_sessions ON public.upload_sessions
    FOR ALL TO aicte_api_writer USING (true) WITH CHECK (true);

-- 5. RLS policies for aicte_api_reader
CREATE POLICY aicte_api_reader_all_documents ON public.documents
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_doc_versions ON public.document_versions
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_doc_types ON public.document_types
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_doc_rules ON public.document_requirement_rules
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_doc_extractions ON public.document_extractions
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_doc_checks ON public.document_check_results
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_doc_renewals ON public.document_renewal_cases
    FOR SELECT TO aicte_api_reader USING (true);

CREATE POLICY aicte_api_reader_all_upload_sessions ON public.upload_sessions
    FOR SELECT TO aicte_api_reader USING (true);
