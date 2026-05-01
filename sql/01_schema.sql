-- ============================================================
-- 01_schema.sql
-- Core table definitions for Nurture-Track
-- Run once in: Supabase Dashboard → SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS public.expenses (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  TIMESTAMPTZ NOT NULL    DEFAULT now(),
    date        DATE        NOT NULL,
    child       TEXT,
    category    TEXT        NOT NULL,
    amount      NUMERIC     NOT NULL,
    image_url   TEXT,
    uploaded_by UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    status      TEXT        NOT NULL    DEFAULT 'Pending'
                            CHECK (status IN ('Pending', 'Acknowledged'))
);
