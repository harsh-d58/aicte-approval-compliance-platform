-- Phase 1, PRD §§3.2–3.3 and 13.1: least-privilege API read role.
-- Applied only by backend/apply_read_runtime_role.py after it creates the
-- aicte_api_reader login role. Its credential never belongs in this file.
-- The verified Supabase subject is set transaction-locally by FastAPI.

CREATE SCHEMA api_private;
REVOKE ALL ON SCHEMA api_private FROM PUBLIC;

CREATE FUNCTION api_private.subject_uuid()
RETURNS uuid
LANGUAGE sql STABLE
SET search_path = pg_catalog
AS $$
    SELECT NULLIF(current_setting('aicte.subject_id', true), '')::uuid
$$;

CREATE FUNCTION api_private.can_read(
    p_permission text, p_institution_id uuid, p_application_id uuid
)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog
AS $$
    SELECT p_permission IN ('institution.read', 'application.read') AND EXISTS (
        SELECT 1
        FROM public.users u
        JOIN public.user_role_assignments a ON a.user_id = u.id
        JOIN public.role_permissions rp ON rp.role_id = a.role_id
        JOIN public.permissions p ON p.id = rp.permission_id
        JOIN public.institutions i ON i.id = p_institution_id
        WHERE u.id = api_private.subject_uuid()
          AND u.identity_subject = u.id::text
          AND u.status = 'active'
          AND a.status = 'active'
          AND a.valid_from <= CURRENT_TIMESTAMP
          AND (a.valid_until IS NULL OR a.valid_until > CURRENT_TIMESTAMP)
          AND p.permission_code = p_permission
          AND (
              (a.scope_type = 'global' AND a.scope_id IS NULL)
              OR (a.scope_type = 'institution' AND a.scope_id = i.id)
              OR (a.scope_type = 'region' AND a.scope_id = i.region_id)
              OR (p_application_id IS NOT NULL
                  AND a.scope_type = 'application' AND a.scope_id = p_application_id)
          )
    )
$$;

REVOKE ALL ON FUNCTION api_private.subject_uuid() FROM PUBLIC;
REVOKE ALL ON FUNCTION api_private.can_read(text, uuid, uuid) FROM PUBLIC;
GRANT USAGE ON SCHEMA public, api_private TO aicte_api_reader;
GRANT EXECUTE ON FUNCTION api_private.subject_uuid() TO aicte_api_reader;
GRANT EXECUTE ON FUNCTION api_private.can_read(text, uuid, uuid) TO aicte_api_reader;
GRANT SELECT ON public.users, public.roles, public.permissions,
    public.role_permissions, public.user_role_assignments,
    public.institutions, public.applications TO aicte_api_reader;
ALTER ROLE aicte_api_reader SET default_transaction_read_only = on;

CREATE POLICY aicte_api_reader_select ON public.users
    FOR SELECT TO aicte_api_reader
    USING (id = api_private.subject_uuid()
           AND identity_subject = id::text AND status = 'active');

CREATE POLICY aicte_api_reader_select ON public.user_role_assignments
    FOR SELECT TO aicte_api_reader
    USING (user_id = api_private.subject_uuid()
           AND status = 'active'
           AND valid_from <= CURRENT_TIMESTAMP
           AND (valid_until IS NULL OR valid_until > CURRENT_TIMESTAMP)
           AND EXISTS (SELECT 1 FROM public.users u WHERE u.id = user_id));

CREATE POLICY aicte_api_reader_select ON public.roles
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.user_role_assignments a
        WHERE a.role_id = roles.id
    ));

CREATE POLICY aicte_api_reader_select ON public.role_permissions
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.user_role_assignments a
        WHERE a.role_id = role_permissions.role_id
    ));

CREATE POLICY aicte_api_reader_select ON public.permissions
    FOR SELECT TO aicte_api_reader
    USING (EXISTS (
        SELECT 1 FROM public.role_permissions rp
        WHERE rp.permission_id = permissions.id
    ));

CREATE POLICY aicte_api_reader_select ON public.institutions
    FOR SELECT TO aicte_api_reader
    USING (api_private.can_read('institution.read', id, NULL));

CREATE POLICY aicte_api_reader_select ON public.applications
    FOR SELECT TO aicte_api_reader
    USING (api_private.can_read('application.read', institution_id, id));
