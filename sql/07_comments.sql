-- ============================================================
-- 07_comments.sql
-- Comments table for per-expense parent communication
-- Run once in: Supabase Dashboard → SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS public.comments (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  TIMESTAMPTZ NOT NULL    DEFAULT now(),
    expense_id  UUID        NOT NULL    REFERENCES public.expenses(id) ON DELETE CASCADE,
    author      TEXT        NOT NULL    CHECK (author IN ('Mom', 'Dad')),
    body        TEXT        NOT NULL
);

CREATE INDEX IF NOT EXISTS comments_expense_id_idx ON public.comments (expense_id);
