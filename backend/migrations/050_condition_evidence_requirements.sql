-- Preserve the institution-facing evidence checklist entered with an undertaking.
ALTER TABLE public.compliance_conditions ADD COLUMN IF NOT EXISTS evidence_requirements jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.compliance_conditions ADD CONSTRAINT condition_evidence_requirements_array
 CHECK (jsonb_typeof(evidence_requirements)='array');
