ALTER TABLE public.expert_availability ADD COLUMN IF NOT EXISTS superseded_at timestamptz;
ALTER TABLE public.expert_availability ADD COLUMN IF NOT EXISTS supersedes_id uuid;
ALTER TABLE public.institution_availability ADD COLUMN IF NOT EXISTS superseded_at timestamptz;
ALTER TABLE public.institution_availability ADD COLUMN IF NOT EXISTS supersedes_id uuid;
ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS issuer text;
ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS reference text;