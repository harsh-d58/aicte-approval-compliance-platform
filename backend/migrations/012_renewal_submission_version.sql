-- Keep original and renewed versions distinct through human verification.
ALTER TABLE public.document_renewal_cases ADD COLUMN IF NOT EXISTS submitted_version_id uuid REFERENCES public.document_versions(id);
