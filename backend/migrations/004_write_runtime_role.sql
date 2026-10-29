-- Phase 1 & 2: Least-privilege API write role (aicte_api_writer).
-- Applied only by backend/apply_write_runtime_role.py after it creates the
-- aicte_api_writer login role. Its credentials never belong in this file.
-- The verified Supabase subject is set transaction-locally by FastAPI.

GRANT USAGE ON SCHEMA public, api_private TO aicte_api_writer;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api_private TO aicte_api_writer;

-- Select privileges on core identity and reference data
GRANT SELECT ON public.users, public.roles, public.permissions,
    public.role_permissions, public.user_role_assignments,
    public.institutions, public.applications TO aicte_api_writer;

-- Mutation privileges on user role assignments (for administrative grant/revoke)
GRANT INSERT, UPDATE ON public.user_role_assignments TO aicte_api_writer;

-- Mutation privileges on business records for workflow mutations
GRANT INSERT, UPDATE ON public.institutions, public.applications TO aicte_api_writer;

-- Append-only privileges on audit events (triggers block UPDATE / DELETE / TRUNCATE)
GRANT INSERT, SELECT ON public.audit_events TO aicte_api_writer;

-- Worker & transaction primitives
GRANT SELECT, INSERT, UPDATE, DELETE ON public.outbox_events TO aicte_api_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.api_idempotency_records TO aicte_api_writer;

-- Ensure default transaction is read-write for this role
ALTER ROLE aicte_api_writer SET default_transaction_read_only = off;

-- RLS policies for aicte_api_writer on identity & access tables
CREATE POLICY aicte_api_writer_select_users ON public.users
    FOR SELECT TO aicte_api_writer
    USING (true);

CREATE POLICY aicte_api_writer_select_roles ON public.roles
    FOR SELECT TO aicte_api_writer
    USING (true);

CREATE POLICY aicte_api_writer_select_permissions ON public.permissions
    FOR SELECT TO aicte_api_writer
    USING (true);

CREATE POLICY aicte_api_writer_select_role_permissions ON public.role_permissions
    FOR SELECT TO aicte_api_writer
    USING (true);

CREATE POLICY aicte_api_writer_select_assignments ON public.user_role_assignments
    FOR SELECT TO aicte_api_writer
    USING (true);

CREATE POLICY aicte_api_writer_insert_assignments ON public.user_role_assignments
    FOR INSERT TO aicte_api_writer
    WITH CHECK (true);

CREATE POLICY aicte_api_writer_update_assignments ON public.user_role_assignments
    FOR UPDATE TO aicte_api_writer
    USING (true)
    WITH CHECK (true);

-- RLS policies for aicte_api_writer on business tables
CREATE POLICY aicte_api_writer_select_institutions ON public.institutions
    FOR SELECT TO aicte_api_writer
    USING (true);

CREATE POLICY aicte_api_writer_insert_institutions ON public.institutions
    FOR INSERT TO aicte_api_writer
    WITH CHECK (true);

CREATE POLICY aicte_api_writer_update_institutions ON public.institutions
    FOR UPDATE TO aicte_api_writer
    USING (true)
    WITH CHECK (true);

CREATE POLICY aicte_api_writer_select_applications ON public.applications
    FOR SELECT TO aicte_api_writer
    USING (true);

CREATE POLICY aicte_api_writer_insert_applications ON public.applications
    FOR INSERT TO aicte_api_writer
    WITH CHECK (true);

CREATE POLICY aicte_api_writer_update_applications ON public.applications
    FOR UPDATE TO aicte_api_writer
    USING (true)
    WITH CHECK (true);

-- RLS policies on audit events
CREATE POLICY aicte_api_writer_insert_audit ON public.audit_events
    FOR INSERT TO aicte_api_writer
    WITH CHECK (true);

CREATE POLICY aicte_api_writer_select_audit ON public.audit_events
    FOR SELECT TO aicte_api_writer
    USING (true);

-- RLS policies on outbox and idempotency
CREATE POLICY aicte_api_writer_all_outbox ON public.outbox_events
    FOR ALL TO aicte_api_writer
    USING (true)
    WITH CHECK (true);

CREATE POLICY aicte_api_writer_all_idempotency ON public.api_idempotency_records
    FOR ALL TO aicte_api_writer
    USING (true)
    WITH CHECK (true);
