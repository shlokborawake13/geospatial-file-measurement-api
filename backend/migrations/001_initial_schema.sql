-- Migration 001: Initial schema
-- Apply via Supabase SQL Editor or psql.
-- Safe to re-run: uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.

-- ── files ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.files (
    id                     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    filename               text        NOT NULL,
    file_type              text        NOT NULL CHECK (file_type IN ('KML', 'SHP_ZIP')),
    storage_path           text        NOT NULL,
    original_crs           text,
    feature_count          integer     CHECK (feature_count >= 0),
    status                 text        NOT NULL CHECK (status IN ('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED')),
    error_message          text,
    processing_duration_ms integer,
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now()
);

-- Add any columns that may be missing from an existing table
ALTER TABLE public.files ADD COLUMN IF NOT EXISTS original_crs           text;
ALTER TABLE public.files ADD COLUMN IF NOT EXISTS feature_count          integer     CHECK (feature_count >= 0);
ALTER TABLE public.files ADD COLUMN IF NOT EXISTS error_message          text;
ALTER TABLE public.files ADD COLUMN IF NOT EXISTS processing_duration_ms integer;
ALTER TABLE public.files ADD COLUMN IF NOT EXISTS updated_at             timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_files_status ON public.files(status);

-- ── features ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.features (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id        uuid        NOT NULL REFERENCES public.files(id) ON DELETE CASCADE,
    feature_index  integer     NOT NULL CHECK (feature_index >= 0),
    geometry_type  text        NOT NULL,
    geometry       jsonb,
    properties     jsonb,
    original_crs   text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE(file_id, feature_index)
);

CREATE INDEX IF NOT EXISTS idx_features_file_id ON public.features(file_id);

-- ── measurements ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.measurements (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id       uuid        NOT NULL REFERENCES public.features(id) ON DELETE CASCADE,
    measurement_type text        CHECK (measurement_type IN ('AREA', 'LENGTH')),
    value            numeric,
    unit             text,
    measurement_crs  text,
    status           text        NOT NULL CHECK (status IN ('SUCCESS', 'NOT_REQUIRED', 'UNSUPPORTED', 'FAILED')),
    error_message    text,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_measurements_feature_id ON public.measurements(feature_id);

-- Refresh PostgREST schema cache so new columns are immediately visible
NOTIFY pgrst, 'reload schema';
