-- Controlled manual institution availability for the prototype portal.
CREATE TABLE IF NOT EXISTS public.institution_availability (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(id),
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL,
    availability_status text NOT NULL CHECK (availability_status IN ('available', 'unavailable')),
    source text NOT NULL DEFAULT 'manual_entry',
    last_confirmed_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid NOT NULL REFERENCES public.users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (end_at > start_at)
);
CREATE INDEX IF NOT EXISTS institution_availability_window ON public.institution_availability(institution_id,start_at,end_at);
ALTER TABLE public.institution_availability ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON public.institution_availability TO aicte_api_writer;
DROP POLICY IF EXISTS prototype_writer_availability ON public.institution_availability;
CREATE POLICY prototype_writer_availability ON public.institution_availability TO aicte_api_writer
USING (EXISTS (SELECT 1 FROM public.institutions i WHERE i.id = institution_id))
WITH CHECK (EXISTS (SELECT 1 FROM public.institutions i WHERE i.id = institution_id));
