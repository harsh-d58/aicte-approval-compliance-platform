-- PRD §13.4: audit rows must be append-only.
-- A separate least-privilege runtime role and protected backups are still required.

CREATE FUNCTION public.reject_audit_event_mutation_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_events are append-only' USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER audit_events_no_update_delete
BEFORE UPDATE OR DELETE ON public.audit_events
FOR EACH ROW EXECUTE FUNCTION public.reject_audit_event_mutation_v1();

CREATE TRIGGER audit_events_no_truncate
BEFORE TRUNCATE ON public.audit_events
FOR EACH STATEMENT EXECUTE FUNCTION public.reject_audit_event_mutation_v1();
