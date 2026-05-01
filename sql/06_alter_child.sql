-- ============================================================
-- 06_alter_child.sql
-- Adds the child column to an existing expenses table
-- Run once if table already exists from 01_schema.sql
-- ============================================================

ALTER TABLE public.expenses
    ADD COLUMN IF NOT EXISTS child TEXT;
