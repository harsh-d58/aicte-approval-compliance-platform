-- The portal projection authorizes parent scopes on the server before returning
-- data. These tables were omitted from previous runtime grants. No owner or
-- BYPASSRLS credential is used by HTTP handlers.
GRANT SELECT ON action_items, audit_anchors, system_settings,
    integration_endpoints, background_jobs TO aicte_api_writer;
GRANT INSERT, UPDATE ON action_items, system_settings, background_jobs,
    integration_endpoints TO aicte_api_writer;
GRANT UPDATE ON users TO aicte_api_writer;
DO $$
DECLARE target text;
BEGIN
  FOREACH target IN ARRAY ARRAY['action_items','audit_anchors','system_settings',
    'integration_endpoints','background_jobs'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', target);
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public'
      AND tablename=target AND policyname='portal_writer_access') THEN
      EXECUTE format('CREATE POLICY portal_writer_access ON public.%I TO aicte_api_writer USING (true) WITH CHECK (true)',target);
    END IF;
  END LOOP;
END $$;
DROP POLICY IF EXISTS portal_writer_user_status ON public.users;
CREATE POLICY portal_writer_user_status ON public.users FOR UPDATE TO aicte_api_writer
  USING (true) WITH CHECK (true);
